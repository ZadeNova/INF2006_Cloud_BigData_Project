# base/ owns only sg-db. sg-alb and sg-app belong to each stack (ec2/, fargate/), which also adds its own
# rule to sg-db allowing 5432 from its own sg-app, so base/ never refers to a stack (ADR-001).
# Chain in every stack: internet -> sg-alb (443/80) -> sg-app (8000) -> sg-db (5432). No port 22 anywhere.
# Terraform removes AWS's default allow-all outbound rule, so sg-db has no egress rules at all.

resource "aws_security_group" "db" {
  name        = "${local.name_prefix}-sg-db"
  description = "RDS: PostgreSQL from the app instances only"
  vpc_id      = aws_vpc.main.id

  tags = { Name = "${local.name_prefix}-sg-db" }
}

# The VPC's built-in default group lets its members talk freely. Adopt it and leave it with no rules,
# so anything accidentally attached to it can reach nothing.
resource "aws_default_security_group" "default" {
  vpc_id = aws_vpc.main.id

  tags = { Name = "${local.name_prefix}-sg-default-deny" }
}
