output "hostname" {
  description = "The HTTPS hostname of this stack."
  value       = local.app_hostname
}

output "alb_dns_name" {
  description = "The ALB's own address, for checks before DNS is trusted."
  value       = module.web_entry.alb_dns_name
}

output "target_group_arn" {
  value = module.web_entry.target_group_arn
}

output "asg_name" {
  description = "Auto Scaling group name, to find its instance for Session Manager."
  value       = aws_autoscaling_group.app.name
}

output "security_group_ids" {
  value = {
    alb = module.web_entry.alb_security_group_id
    app = module.web_entry.app_security_group_id
  }
}

output "log_group_name" {
  value = module.web_entry.log_group_name
}

output "image_digest" {
  description = "The exact image the instances run (from var.image_tag)."
  value       = data.aws_ecr_image.app.image_digest
}

output "web_acl_name" {
  description = "The WAF web ACL on the ALB (for the security test and its sampled requests)."
  value       = module.web_entry.web_acl_name
}
