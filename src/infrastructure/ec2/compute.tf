# The app instances: a launch template (the recipe for one instance) and an Auto Scaling group (keeps the right
# number running and replaces an instance that stops answering the ALB). Exactly one instance for now.

locals {
  # ECR registry host (the part of the repository URL before the first "/"), for docker login.
  ecr_registry = split("/", local.base.ecr_repository_url)[0]
  # Run by digest, never by tag: every instance runs exactly the same image bytes.
  image_ref = "${local.base.ecr_repository_url}@${data.aws_ecr_image.app.image_digest}"
  # CPU credits exist only on burstable (t) types; the credit setting is rejected on any other family.
  burstable = startswith(var.instance_type, "t")
}

resource "aws_launch_template" "app" {
  name                   = "${local.stack_prefix}-lt"
  image_id               = data.aws_ssm_parameter.al2023_ami.insecure_value # an AMI ID, not a secret; shown in plans
  instance_type          = var.instance_type                                # ADR-007
  update_default_version = true

  # A t3 from a launch template defaults to "unlimited" credits, billed extra under load. Standard keeps the cost
  # fixed. Not used for the non-burstable default, so a comparison run is never confounded by credits.
  dynamic "credit_specification" {
    for_each = local.burstable ? [1] : []
    content {
      cpu_credits = "standard"
    }
  }

  iam_instance_profile {
    arn = data.aws_iam_instance_profile.lab.arn
  }

  # A public IP lets the instance reach ECR, Secrets Manager, S3, CloudWatch and SSM without a NAT gateway.
  # Nothing can connect in: sg-app only accepts port 8000 from sg-alb.
  network_interfaces {
    associate_public_ip_address = true
    security_groups             = [aws_security_group.app.id]
    delete_on_termination       = true
  }

  # IMDSv2 only (session tokens; blocks request-forgery credential theft). Hop limit 2 so the Docker containers,
  # one network hop further away, can still get the instance role's credentials.
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 2
  }

  block_device_mappings {
    device_name = "/dev/xvda" # the AL2023 root volume
    ebs {
      volume_size           = 16
      volume_type           = "gp3"
      encrypted             = true
      delete_on_termination = true
    }
  }

  user_data = base64encode(templatefile("${path.module}/user_data.sh.tftpl", {
    region        = var.region
    ecr_registry  = local.ecr_registry
    image_ref     = local.image_ref
    log_group     = aws_cloudwatch_log_group.app.name
    release_id    = var.image_tag
    app_hostname  = local.app_hostname
    trust_proxy   = "true" # behind the ALB; "false" here would redirect-loop with SECURE_SSL_REDIRECT
    secret_prefix = local.name_prefix
  }))

  tag_specifications {
    resource_type = "instance"
    tags          = merge(data.aws_default_tags.current.tags, { Name = "${local.stack_prefix}-app" })
  }

  tag_specifications {
    resource_type = "volume"
    tags          = merge(data.aws_default_tags.current.tags, { Name = "${local.stack_prefix}-app-root" })
  }

  tags = { Name = "${local.stack_prefix}-lt" }
}

resource "aws_autoscaling_group" "app" {
  name                = "${local.stack_prefix}-asg"
  min_size            = 1
  max_size            = 1 # raised to 2 with the scaling policy in the next step
  desired_capacity    = 1
  vpc_zone_identifier = values(local.base.public_subnet_ids)

  # Replace an instance when the ALB says it is unhealthy, not only when the machine itself fails (ADR-008).
  # The grace period covers boot: Docker install, image pull, first health check.
  target_group_arns         = [aws_lb_target_group.app.arn]
  health_check_type         = "ELB"
  health_check_grace_period = 300

  # A new template version (a new image or AMI) applies to instances launched from then on. Running instances are
  # replaced only by an instance refresh: aws autoscaling start-instance-refresh (that time is a measured result).
  launch_template {
    id      = aws_launch_template.app.id
    version = aws_launch_template.app.latest_version
  }
}
