# The app as an ECS task on Fargate: a cluster (a name to group the work under), a task definition (the recipe for
# one container) and a service (keeps the wanted number of tasks running and replaces one that stops answering the ALB).
# ADR-015.

locals {
  # Run by digest, never by tag: every task runs exactly the same image bytes, and the same ones the ec2 stack runs.
  image_ref = "${local.base.ecr_repository_url}@${data.aws_ecr_image.app.image_digest}"

  # The ALB health-checks a task by its private IP, and Django accepts that Host only if DJANGO_HEALTH_PROBE_HOST
  # names it (ADR-016). The IP exists only once the task runs, so this start command reads it from the ECS metadata
  # endpoint and then starts the image's own command unchanged. If the lookup fails the task stops (set -e) instead
  # of running unhealthy. The gunicorn line is the CMD of src/Dockerfile: keep them the same (ADR-016).
  web_command = <<-EOT
    set -eu
    IP=$(python -c 'import json, os, urllib.request as u; print(json.load(u.urlopen(os.environ["ECS_CONTAINER_METADATA_URI_V4"] + "/task", timeout=5))["Containers"][0]["Networks"][0]["IPv4Addresses"][0])')
    export DJANGO_HEALTH_PROBE_HOST="$IP:8000"
    exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 30 --error-logfile - --no-control-socket
  EOT
}

resource "aws_ecs_cluster" "app" {
  name = "${local.stack_prefix}-cluster"

  # Container Insights is a per-metric charge and not needed for the comparison (ADR-015); the harness uses the
  # service's own CPU and memory metrics and the ALB's healthy-host count.
  setting {
    name  = "containerInsights"
    value = "disabled"
  }

  tags = { Name = "${local.stack_prefix}-cluster" }
}

resource "aws_ecs_task_definition" "app" {
  family                   = "${local.stack_prefix}-app"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc" # one network interface per task, with its own private IP
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = data.aws_iam_role.lab.arn
  task_role_arn            = data.aws_iam_role.lab.arn

  # x86_64, like the c5.large and the image built on the laptop.
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([
    {
      name      = "web"
      image     = local.image_ref
      essential = true
      command   = ["sh", "-c", local.web_command]

      portMappings = [{ containerPort = 8000, protocol = "tcp" }]

      # The shared application settings (ADR-014) plus the one secret name this container may read. Secret values are
      # never here: the app fetches its own with the task role at start-up.
      environment = concat(
        [for k, v in module.web_entry.app_environment : { name = k, value = v }],
        [{ name = "AWS_SECRET_ID", value = "${local.name_prefix}/web" }],
      )

      stopTimeout = 30 # seconds Gunicorn gets to finish requests after SIGTERM; matches the 30 s deregistration delay

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = module.web_entry.log_group_name
          awslogs-region        = var.region
          awslogs-stream-prefix = "web"
        }
      }
    }
  ])

  tags = { Name = "${local.stack_prefix}-app" }
}

resource "aws_ecs_service" "app" {
  name            = "${local.stack_prefix}-service"
  cluster         = aws_ecs_cluster.app.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.desired_capacity # reset to this on every apply (ADR-013)
  launch_type     = "FARGATE"

  # A task that has just started is not judged by the ALB for this long: image pull, start-up, first health checks.
  health_check_grace_period_seconds = 120

  # Rolling update: start the new task before stopping the old one, never below the wanted count; if the new task
  # keeps failing, stop and go back to the old one.
  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  # Public IP so the task reaches ECR, Secrets Manager and CloudWatch without a NAT gateway. Nothing can connect in:
  # sg-app only accepts port 8000 from sg-alb.
  network_configuration {
    subnets          = values(local.base.public_subnet_ids)
    security_groups  = [module.web_entry.app_security_group_id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = module.web_entry.target_group_arn
    container_name   = "web"
    container_port   = 8000
  }

  # The apply returns when the service is steady, so a failed start shows as a failed apply, not a quiet loop.
  wait_for_steady_state = true

  # The target group must be attached to a listener before a service can register tasks with it.
  depends_on = [module.web_entry]

  tags = { Name = "${local.stack_prefix}-service" }
}
