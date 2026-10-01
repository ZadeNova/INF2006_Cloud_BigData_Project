# RDS PostgreSQL 17 in the private subnets (ADR-004). One database shared by both variants; each stack adds
# its own sg-db ingress rule from its own sg-app, so nothing but a stack's app compute can reach it.
# No initial database: db_bootstrap creates it, owned by the migration login. An initial database
# here would be owned by the master, and bootstrap refuses foreign-owned databases.

# Which subnets RDS may place the instance in. It must cover two AZs, even for a single-AZ instance.
resource "aws_db_subnet_group" "main" {
  name       = "${local.name_prefix}-db-subnets"
  subnet_ids = [for s in aws_subnet.private : s.id]

  tags = { Name = "${local.name_prefix}-db-subnets" }
}

# Server settings. rds.force_ssl is already on by default for PostgreSQL 17; setting it here makes the
# "TLS required" control visible in code and in the evidence.
resource "aws_db_parameter_group" "main" {
  name   = "${local.name_prefix}-pg17"
  family = "postgres17"

  parameter {
    name         = "rds.force_ssl"
    value        = "1"
    apply_method = "pending-reboot" # what RDS stores for this parameter; "immediate" would show a diff on every plan
  }

  tags = { Name = "${local.name_prefix}-pg17" }
}

# PostgreSQL's own server log, exported by RDS. RDS would otherwise create this group itself with no
# expiry; creating it first (with the exact name RDS uses) caps it at 7 days.
resource "aws_cloudwatch_log_group" "db" {
  name              = "/aws/rds/instance/${local.name_prefix}-db/postgresql"
  retention_in_days = 7

  tags = { Name = "${local.name_prefix}-log-db" }
}

resource "aws_db_instance" "main" {
  identifier     = "${local.name_prefix}-db"
  engine         = "postgres"
  engine_version = "17"                  # major only; the actual minor is shown as engine_version_actual and recorded in the runbook
  instance_class = var.db_instance_class # ADR-004: one size for every recorded run

  allocated_storage = 20
  storage_type      = "gp3"
  storage_encrypted = true # AWS-managed key

  # RDS generates the master password and keeps it in its own Secrets Manager secret, rotated every
  # 7 days. It never appears in Terraform code or state. Copy it into the bootstrap secret only
  # immediately before a db_bootstrap run.
  username                    = "inf2006_master"
  manage_master_user_password = true

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = false
  multi_az               = false # cost; the subnet group already spans two AZs, so this is a one-setting change
  parameter_group_name   = aws_db_parameter_group.main.name

  # Point-in-time restore to any second in the last 7 days; free up to the size of the database storage.
  backup_retention_period = 7
  copy_tags_to_snapshot   = true

  # Send the PostgreSQL log to the group above (connection failures and errors, for the DB outage demo).
  enabled_cloudwatch_logs_exports = ["postgresql"]

  auto_minor_version_upgrade = true
  apply_immediately          = true # otherwise changes wait for the weekly maintenance window

  # Lab teardown: destroy must finish in one command and leave nothing billing behind. A manual
  # snapshot during the stage 5 evidence runs is the recovery evidence, not a final snapshot.
  skip_final_snapshot      = true
  deletion_protection      = false
  delete_automated_backups = true

  tags = { Name = "${local.name_prefix}-db" }

  # The log group must exist before RDS starts exporting, or RDS creates its own without retention.
  depends_on = [aws_cloudwatch_log_group.db]
}
