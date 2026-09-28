# Log group now; the SNS topic below is wired to CloudWatch alarms in stage 4 (target health, 5xx rate).

resource "aws_cloudwatch_log_group" "app" {
  name              = "/${local.name_prefix}/app"
  retention_in_days = 7 # cost control: unbounded retention on a lab budget is not worth it

  tags = { Name = "${local.name_prefix}-log-app" }
}

resource "aws_sns_topic" "alarms" {
  name = "${local.name_prefix}-alarms"

  tags = { Name = "${local.name_prefix}-alarms" }
}

# AWS emails var.alarm_email a confirmation link after apply. The subscription is "PendingConfirmation"
# until someone clicks it; Terraform cannot confirm it for them, so this is a stage 1 acceptance check.
resource "aws_sns_topic_subscription" "alarm_email" {
  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email"
  endpoint  = var.alarm_email
}
