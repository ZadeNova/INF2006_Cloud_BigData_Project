# The SNS topic below is wired to CloudWatch alarms in each stack. The app log group lives in the stacks.

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
