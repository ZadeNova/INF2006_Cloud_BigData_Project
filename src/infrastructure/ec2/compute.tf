# The app instances: a launch template (the recipe for one instance) and an Auto Scaling group (keeps the right
# number running and replaces an instance that stops answering the ALB). One instance normally, two at most (scaling.tf).

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

  # Detailed monitoring: instance metrics every minute instead of every five (ADR-013). A scale-out that takes two
  # minutes cannot be seen on a five-minute graph. Small extra charge per instance; it applies to instances launched
  # from this template version onward.
  monitoring {
    enabled = true
  }

  # A public IP lets the instance reach ECR, Secrets Manager, S3, CloudWatch and SSM without a NAT gateway.
  # Nothing can connect in: sg-app only accepts port 8000 from sg-alb.
  network_interfaces {
    associate_public_ip_address = true
    security_groups             = [module.web_entry.app_security_group_id]
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
    region       = var.region
    ecr_registry = local.ecr_registry
    image_ref    = local.image_ref
    log_group    = module.web_entry.log_group_name
    # The shared application settings (ADR-014), one KEY=value line each; the probe host is added at boot.
    app_env       = join("\n", [for k, v in module.web_entry.app_environment : "${k}=${v}"])
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
  min_size            = var.min_capacity # ADR-011 defaults: 1 to 2 instances. ADR-013: variables so a fixed-capacity
  max_size            = var.max_capacity # run can pin all three to the same number and take scaling out of the result
  desired_capacity    = var.desired_capacity
  vpc_zone_identifier = values(local.base.public_subnet_ids)

  # Replace an instance when the ALB says it is unhealthy, not only when the machine itself fails (ADR-008).
  # The grace period covers boot: Docker install, image pull, first health check.
  target_group_arns         = [module.web_entry.target_group_arn]
  health_check_type         = "ELB"
  health_check_grace_period = 300

  # One-minute group metrics (instances wanted, in service, pending, terminating) for the scale-out and replacement
  # timelines (ADR-013). They are off by default and free to publish.
  metrics_granularity = "1Minute"
  enabled_metrics = [
    "GroupDesiredCapacity",
    "GroupInServiceInstances",
    "GroupPendingInstances",
    "GroupTerminatingInstances",
  ]

  # A new template version (a new image or AMI) applies to instances launched from then on. Running instances are
  # replaced only by an instance refresh: aws autoscaling start-instance-refresh (that time is a measured result).
  launch_template {
    id      = aws_launch_template.app.id
    version = aws_launch_template.app.latest_version
  }
}
