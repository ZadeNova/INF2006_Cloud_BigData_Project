# Horizontal scaling (ADR-011, ADR-017): Application Auto Scaling adds a task when the average requests per task per
# minute rise above the target and removes one when they fall well below it. Same metric, target and limits as the
# ec2 stack, so the two variants scale on the same signal.

resource "aws_appautoscaling_target" "app" {
  service_namespace  = "ecs"
  scalable_dimension = "ecs:service:DesiredCount"
  resource_id        = "service/${aws_ecs_cluster.app.name}/${aws_ecs_service.app.name}"
  min_capacity       = var.min_capacity
  max_capacity       = var.max_capacity
}

resource "aws_appautoscaling_policy" "requests" {
  name               = "${local.stack_prefix}-requests-per-target"
  policy_type        = "TargetTrackingScaling"
  service_namespace  = aws_appautoscaling_target.app.service_namespace
  scalable_dimension = aws_appautoscaling_target.app.scalable_dimension
  resource_id        = aws_appautoscaling_target.app.resource_id

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ALBRequestCountPerTarget"
      resource_label         = "${module.web_entry.alb_arn_suffix}/${module.web_entry.target_group_arn_suffix}"
    }
    target_value = var.scale_target_requests

    # Seconds after a scaling action before the next one of the same kind (ADR-017). With a maximum of 2 tasks there
    # is only one scale-out step, so the out value barely matters; the in value keeps the task from flapping.
    scale_out_cooldown = 300
    scale_in_cooldown  = 300
  }
}
