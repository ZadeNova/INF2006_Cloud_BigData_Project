output "hostname" {
  description = "The HTTPS hostname of this stack."
  value       = local.app_hostname
}

output "alb_dns_name" {
  description = "The ALB's own address, for checks before DNS is trusted."
  value       = aws_lb.app.dns_name
}

output "target_group_arn" {
  value = aws_lb_target_group.app.arn
}

output "asg_name" {
  description = "Auto Scaling group name, to find its instance for Session Manager."
  value       = aws_autoscaling_group.app.name
}

output "security_group_ids" {
  value = {
    alb = aws_security_group.alb.id
    app = aws_security_group.app.id
  }
}

output "log_group_name" {
  value = aws_cloudwatch_log_group.app.name
}

output "image_digest" {
  description = "The exact image the instances run (from var.image_tag)."
  value       = data.aws_ecr_image.app.image_digest
}

output "web_acl_name" {
  description = "The WAF web ACL on the ALB (for the security test and its sampled requests)."
  value       = aws_wafv2_web_acl.app.name
}
