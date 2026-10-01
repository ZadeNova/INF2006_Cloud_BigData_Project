# The public entry point: an internet-facing ALB that ends TLS, health-checks the app and replaces nothing itself
# (the ASG does, on its health signal). ADR-008.

resource "aws_lb" "app" {
  name               = "${local.stack_prefix}-alb"
  load_balancer_type = "application"
  internal           = false
  security_groups    = [aws_security_group.alb.id]
  subnets            = values(local.base.public_subnet_ids)

  drop_invalid_header_fields = true # refuse malformed headers rather than pass them to Gunicorn

  tags = { Name = "${local.stack_prefix}-alb" }
}

resource "aws_lb_target_group" "app" {
  name     = "${local.stack_prefix}-tg"
  port     = 8000
  protocol = "HTTP"
  vpc_id   = local.base.vpc_id

  # No stickiness: sessions and carts live in PostgreSQL, so any instance can serve any request.
  deregistration_delay = 30 # ADR-008: seconds a draining target keeps finishing requests; sets scale-in and replacement time

  # The probe goes to the instance's private IP, so Django accepts it through DJANGO_HEALTH_PROBE_HOST
  # (set in user data) and does not redirect it to HTTPS.
  health_check {
    path                = "/health/"
    matcher             = "200"
    interval            = 10 # ADR-008: with the two thresholds, sets detection and recovery time
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  tags = { Name = "${local.stack_prefix}-tg" }
}

# HTTP only redirects, permanently, to HTTPS.
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.app.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.app.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06" # TLS 1.2 and 1.3 only
  certificate_arn   = local.base.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

# The hostname follows the ALB: a recreated ALB needs no DNS edit.
resource "aws_route53_record" "app" {
  zone_id = local.base.route53_zone_id
  name    = local.app_hostname
  type    = "A"

  alias {
    name                   = aws_lb.app.dns_name
    zone_id                = aws_lb.app.zone_id
    evaluate_target_health = true
  }
}
