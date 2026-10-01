# The interface to ec2/ and fargate/: they read these through terraform_remote_state (ADR-001).
# `base/` never reads a stack. `terraform output -json` gives a machine-readable form for scripts.

output "vpc_id" {
  description = "VPC ID for the stacks' security groups and target groups."
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "Public subnet IDs by AZ key (a, b): each stack's ALB and app compute."
  value       = { for k, s in aws_subnet.public : k => s.id }
}

output "private_subnet_ids" {
  description = "Private subnet IDs by AZ key (a, b): the RDS subnet group."
  value       = { for k, s in aws_subnet.private : k => s.id }
}

output "sg_db_id" {
  description = "sg-db. Each stack adds its own ingress rule on 5432 from its own sg-app."
  value       = aws_security_group.db.id
}

output "s3_bucket_name" {
  description = "The bucket's actual name (prefix plus a random suffix), for the CLI push/import commands."
  value       = data.aws_s3_bucket.main.id
}

output "s3_bucket_arn" {
  description = "For the IAM reference policies and the S3 access tests."
  value       = data.aws_s3_bucket.main.arn
}

output "ecr_repository_url" {
  description = "docker push target, e.g. <account>.dkr.ecr.us-east-1.amazonaws.com/inf2006-grp21-app."
  value       = aws_ecr_repository.app.repository_url
}

output "ecr_repository_name" {
  description = "Repository name, for the stacks' image digest lookup."
  value       = aws_ecr_repository.app.name
}

output "secret_arns" {
  description = "web/migration/trainer/bootstrap secret ARNs."
  value       = { for k, s in aws_secretsmanager_secret.app : k => s.arn }
}

output "sns_topic_arn" {
  description = "Alarm topic, wired to each stack's CloudWatch alarms."
  value       = aws_sns_topic.alarms.arn
}

output "route53_zone_id" {
  description = "Hosted zone ID: each stack adds its alias record here."
  value       = aws_route53_zone.main.zone_id
}

output "route53_name_servers" {
  description = "The four name servers to enter at Namecheap (Custom DNS) once the zone exists."
  value       = aws_route53_zone.main.name_servers
}

output "db_host" {
  description = "RDS endpoint hostname: the POSTGRES_HOST value in the web, migration, trainer and bootstrap secrets."
  value       = aws_db_instance.main.address
}

output "db_engine_version" {
  description = "The actual PostgreSQL version RDS chose within major 17, for the runbook."
  value       = aws_db_instance.main.engine_version_actual
}

output "db_master_secret_arn" {
  description = "The secret RDS created for the master login. Copy its username/password into the bootstrap secret right before each db_bootstrap run (it rotates every 7 days)."
  value       = aws_db_instance.main.master_user_secret[0].secret_arn
}
