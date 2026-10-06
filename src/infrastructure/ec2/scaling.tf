# Horizontal scaling (ADR-011): the ASG adds an instance when the average requests per instance per minute rise above
# the target, and removes one when they fall well below it. The ALB already spreads requests, and sessions and carts
# live in PostgreSQL, so a second instance serves any request the first would have.

resource "aws_autoscaling_policy" "requests" {
  name                   = "${local.stack_prefix}-requests-per-target"
  autoscaling_group_name = aws_autoscaling_group.app.name
  policy_type            = "TargetTrackingScaling"

  # Seconds a new instance is left out of the average while it boots (Docker, image pull, first health check).
  estimated_instance_warmup = 240

  target_tracking_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ALBRequestCountPerTarget"
      resource_label         = "${module.web_entry.alb_arn_suffix}/${module.web_entry.target_group_arn_suffix}"
    }
    target_value = var.scale_target_requests
  }

  # The target group must be attached to a listener before the metric exists.
  depends_on = [module.web_entry]
}
