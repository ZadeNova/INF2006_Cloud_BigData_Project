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

output "cluster_name" {
  description = "ECS cluster name, for run-task, stop-task and the load-test captures."
  value       = aws_ecs_cluster.app.name
}

output "service_name" {
  description = "ECS service name."
  value       = aws_ecs_service.app.name
}

output "task_definition_arn" {
  description = "The current task definition revision, for the one-off jobs (aws ecs run-task, scripts/jobs.sh fargate)."
  value       = aws_ecs_task_definition.app.arn
}

output "subnet_ids" {
  description = "Public subnets, for run-task network settings."
  value       = values(local.base.public_subnet_ids)
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
  description = "The exact image the tasks run (from var.image_tag)."
  value       = data.aws_ecr_image.app.image_digest
}

output "web_acl_name" {
  description = "The WAF web ACL on the ALB (for the security test and its sampled requests)."
  value       = module.web_entry.web_acl_name
}
