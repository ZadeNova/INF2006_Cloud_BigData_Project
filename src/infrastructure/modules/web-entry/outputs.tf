output "app_environment" {
  description = "Non-secret environment variables for the app container (name to value)."
  value       = local.app_environment
}

output "app_security_group_id" {
  description = "sg-app: attach it to the instances or tasks (port 8000 from the ALB only)."
  value       = aws_security_group.app.id
}

output "alb_security_group_id" {
  value = aws_security_group.alb.id
}

output "target_group_arn" {
  description = "Register the instances (via the Auto Scaling group) or the tasks (via the ECS service) here."
  value       = aws_lb_target_group.app.arn
}

output "target_group_arn_suffix" {
  description = "CloudWatch dimension value (targetgroup/<name>/<id>); also half of the scaling policy's resource label."
  value       = aws_lb_target_group.app.arn_suffix
}

output "alb_arn_suffix" {
  description = "CloudWatch dimension value (app/<name>/<id>)."
  value       = aws_lb.app.arn_suffix
}

output "alb_dns_name" {
  value = aws_lb.app.dns_name
}

output "log_group_name" {
  value = aws_cloudwatch_log_group.app.name
}

output "web_acl_name" {
  description = "The WAF web ACL on the ALB (for the security test and its sampled requests)."
  value       = aws_wafv2_web_acl.app.name
}
