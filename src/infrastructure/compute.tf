# The app instances: a launch template (the recipe for one instance) and an Auto Scaling group (keeps
# the right number running). Stage 2: exactly one instance, used to run the one-off database jobs.

locals {
  # ECR registry host (the part of the repository URL before the first "/"), for docker login.
  ecr_registry = split("/", aws_ecr_repository.app.repository_url)[0]
  # Run by digest, never by tag: every instance runs exactly the same image bytes.
  image_ref = "${aws_ecr_repository.app.repository_url}@${data.aws_ecr_image.app.image_digest}"
}

resource "aws_launch_template" "app" {
  name                   = "${local.name_prefix}-app-lt"
  image_id               = data.aws_ssm_parameter.al2023_ami.insecure_value # an AMI ID, not a secret; shown in plans
  instance_type          = var.instance_type
  update_default_version = true

  iam_instance_profile {
    arn = data.aws_iam_instance_profile.lab.arn
  }

  # A public IP lets the instance reach ECR, Secrets Manager, S3, CloudWatch and SSM without a NAT
  # gateway. Nothing can connect in: sg-app only accepts port 8000 from sg-alb.
  network_interfaces {
    associate_public_ip_address = true
    security_groups             = [aws_security_group.app.id]
    delete_on_termination       = true
  }

  # IMDSv2 only (session tokens; blocks request-forgery credential theft). Hop limit 2 so the Docker
  # containers, one network hop further away, can still get the instance role's credentials.
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
    app_hostname  = var.app_hostname
    trust_proxy   = "false" # no ALB until stage 3; then "true"
    secret_prefix = local.name_prefix
  }))

  tag_specifications {
    resource_type = "instance"
    tags          = merge(data.aws_default_tags.current.tags, { Name = "${local.name_prefix}-app" })
  }

  tag_specifications {
    resource_type = "volume"
    tags          = merge(data.aws_default_tags.current.tags, { Name = "${local.name_prefix}-app-root" })
  }

  tags = { Name = "${local.name_prefix}-app-lt" }
}

resource "aws_autoscaling_group" "app" {
  name                = "${local.name_prefix}-app-asg"
  min_size            = 1
  max_size            = 1 # stage 4 raises this to 2 for the scaling tests
  desired_capacity    = 1
  vpc_zone_identifier = [for s in aws_subnet.public : s.id]

  # Replace an instance only if the machine itself fails. Stage 3 switches to ELB (the app's /health/).
  health_check_type         = "EC2"
  health_check_grace_period = 300

  # New template versions (a new image or AMI) apply to instances launched from then on. Running
  # instances are not replaced automatically; start an instance refresh when you choose to.
  launch_template {
    id      = aws_launch_template.app.id
    version = aws_launch_template.app.latest_version
  }
}
