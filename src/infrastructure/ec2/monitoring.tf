# This stack's own log group (the web container and the one-off jobs write here). Alarms and the 5xx metric
# filter are added with scaling, in the next step.

resource "aws_cloudwatch_log_group" "app" {
  name              = "/${local.stack_prefix}/app"
  retention_in_days = 7 # cost control: unbounded retention on a lab budget is not worth it

  tags = { Name = "${local.stack_prefix}-log-app" }
}
