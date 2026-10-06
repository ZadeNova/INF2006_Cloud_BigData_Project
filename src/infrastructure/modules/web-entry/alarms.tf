# Alarms that email the SNS topic from base/ (ADR-012). Each looks at one thing a person would act on.

locals {
  alb_dimensions = {
    LoadBalancer = aws_lb.app.arn_suffix
    TargetGroup  = aws_lb_target_group.app.arn_suffix
  }
}

# An instance the ALB has marked unhealthy: the app or the machine is failing its /health/ check.
resource "aws_cloudwatch_metric_alarm" "unhealthy_hosts" {
  alarm_name          = "${var.name}-unhealthy-hosts"
  alarm_description   = "At least one target has failed its /health/ check for 2 minutes"
  namespace           = "AWS/ApplicationELB"
  metric_name         = "UnHealthyHostCount"
  dimensions          = local.alb_dimensions
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 2
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [var.sns_topic_arn]
  ok_actions          = [var.sns_topic_arn]
}

# Nothing is serving: no healthy target at all. Missing data counts as breaching, because no data means no targets.
resource "aws_cloudwatch_metric_alarm" "no_healthy_hosts" {
  alarm_name          = "${var.name}-no-healthy-hosts"
  alarm_description   = "No healthy target behind the load balancer for 2 minutes: the shop is down"
  namespace           = "AWS/ApplicationELB"
  metric_name         = "HealthyHostCount"
  dimensions          = local.alb_dimensions
  statistic           = "Minimum"
  period              = 60
  evaluation_periods  = 2
  threshold           = 1
  comparison_operator = "LessThanThreshold"
  treat_missing_data  = "breaching"
  alarm_actions       = [var.sns_topic_arn]
  ok_actions          = [var.sns_topic_arn]
}

# The app itself answering with server errors (not the ALB or a target that is gone).
resource "aws_cloudwatch_metric_alarm" "target_5xx" {
  alarm_name          = "${var.name}-target-5xx"
  alarm_description   = "The app returned more than 5 server errors in a minute, twice running"
  namespace           = "AWS/ApplicationELB"
  metric_name         = "HTTPCode_Target_5XX_Count"
  dimensions          = local.alb_dimensions
  statistic           = "Sum"
  period              = 60
  evaluation_periods  = 2
  threshold           = 5
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [var.sns_topic_arn]
  ok_actions          = [var.sns_topic_arn]
}

# Saved Logs Insights queries over the app's JSON log lines (fields: ts, level, logger, message, status, request_id).
# Run them from CloudWatch > Logs Insights > Saved queries; export a result as the monitoring evidence.
resource "aws_cloudwatch_query_definition" "recent_problems" {
  name            = "${var.name}/recent-errors-and-security-warnings"
  log_group_names = [aws_cloudwatch_log_group.app.name]
  query_string    = <<-EOT
    fields @timestamp, level, logger, status, request_id, message
    | filter level in ["ERROR", "WARNING"]
    | sort @timestamp desc
    | limit 50
  EOT
}

resource "aws_cloudwatch_query_definition" "problems_per_minute" {
  name            = "${var.name}/errors-and-warnings-per-minute"
  log_group_names = [aws_cloudwatch_log_group.app.name]
  query_string    = <<-EOT
    filter level in ["ERROR", "WARNING"]
    | stats count(*) as events by bin(1m), level
    | sort bin(1m) desc
  EOT
}
