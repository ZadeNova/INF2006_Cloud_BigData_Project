# Values later stages, the runbook and step 8's CLI commands read. `terraform output` prints these
# after apply; `terraform output -json` gives a machine-readable form for scripts.

output "vpc_id" {
  description = "VPC ID, needed by stage 2's DB subnet group and stage 3's ALB/launch template."
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "Public subnet IDs by AZ key (a, b) — the ALB and app instances."
  value       = { for k, s in aws_subnet.public : k => s.id }
}

output "private_subnet_ids" {
  description = "Private subnet IDs by AZ key (a, b) — RDS's subnet group."
  value       = { for k, s in aws_subnet.private : k => s.id }
}

output "security_group_ids" {
  description = "sg-alb, sg-app, sg-db, referenced when attaching the ALB, launch template and RDS instance."
  value = {
    alb = aws_security_group.alb.id
    app = aws_security_group.app.id
    db  = aws_security_group.db.id
  }
}

output "s3_bucket_name" {
  description = "The bucket's actual name (prefix plus AWS's random suffix), for the CLI push/import commands."
  value       = data.aws_s3_bucket.main.id
}

output "s3_bucket_arn" {
  description = "For writing IAM reference policies and the S3 access tests."
  value       = data.aws_s3_bucket.main.arn
}

output "ecr_repository_url" {
  description = "docker push target, e.g. <account>.dkr.ecr.us-east-1.amazonaws.com/inf2006-grp21-app."
  value       = aws_ecr_repository.app.repository_url
}

output "secret_arns" {
  description = "web/migration/trainer/bootstrap secret ARNs, for step 8's put-secret-value commands and the IAM reference policies."
  value       = { for k, s in aws_secretsmanager_secret.app : k => s.arn }
}

output "log_group_name" {
  description = "CloudWatch log group the boot script's awslogs driver writes to."
  value       = aws_cloudwatch_log_group.app.name
}

output "sns_topic_arn" {
  description = "Alarm topic, wired to CloudWatch alarms in stage 4."
  value       = aws_sns_topic.alarms.arn
}

# ---- Stage 2 ----

output "db_host" {
  description = "RDS endpoint hostname: the POSTGRES_HOST value added to the web, migration, trainer and bootstrap secrets."
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

output "asg_name" {
  description = "Auto Scaling group name, to find its instance for Session Manager."
  value       = aws_autoscaling_group.app.name
}

output "image_digest" {
  description = "The exact image the instances run (from var.image_tag)."
  value       = data.aws_ecr_image.app.image_digest
}
