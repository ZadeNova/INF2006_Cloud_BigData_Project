# The stack's own log group (the web container and the one-off jobs write here).

resource "aws_cloudwatch_log_group" "app" {
  name              = "/${var.name}/app"
  retention_in_days = 7 # cost control: unbounded retention on a lab budget is not worth it

  tags = { Name = "${var.name}-log-app" }
}
