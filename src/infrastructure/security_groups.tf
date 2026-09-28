# The chain: internet -> sg-alb (443/80) -> sg-app (8000) -> sg-db (5432). No port 22 anywhere.
# Rules are separate resources so sg-alb and sg-app can reference each other without a creation cycle.
# Terraform removes AWS's default allow-all outbound rule, so only the egress rules below exist.

resource "aws_security_group" "alb" {
  name        = "${local.name_prefix}-sg-alb"
  description = "ALB: HTTPS and HTTP-redirect from the internet"
  vpc_id      = aws_vpc.main.id

  tags = { Name = "${local.name_prefix}-sg-alb" }
}

resource "aws_security_group" "app" {
  name        = "${local.name_prefix}-sg-app"
  description = "App instances: port 8000 from the ALB only"
  vpc_id      = aws_vpc.main.id

  tags = { Name = "${local.name_prefix}-sg-app" }
}

resource "aws_security_group" "db" {
  name        = "${local.name_prefix}-sg-db"
  description = "RDS: PostgreSQL from the app instances only"
  vpc_id      = aws_vpc.main.id

  tags = { Name = "${local.name_prefix}-sg-db" }
}

# --- sg-alb ---

resource "aws_vpc_security_group_ingress_rule" "alb_https" {
  security_group_id = aws_security_group.alb.id
  description       = "HTTPS from the internet"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}

resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  security_group_id = aws_security_group.alb.id
  description       = "HTTP from the internet, only to redirect to HTTPS"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
}

resource "aws_vpc_security_group_egress_rule" "alb_to_app" {
  security_group_id            = aws_security_group.alb.id
  description                  = "Forward requests and health checks to the app"
  referenced_security_group_id = aws_security_group.app.id
  ip_protocol                  = "tcp"
  from_port                    = 8000
  to_port                      = 8000
}

# --- sg-app ---
# Inbound
resource "aws_vpc_security_group_ingress_rule" "app_from_alb" {
  security_group_id            = aws_security_group.app.id
  description                  = "Gunicorn, from the ALB only"
  referenced_security_group_id = aws_security_group.alb.id
  ip_protocol                  = "tcp"
  from_port                    = 8000
  to_port                      = 8000
}
# Outbound
resource "aws_vpc_security_group_egress_rule" "app_https" {
  security_group_id = aws_security_group.app.id
  description       = "HTTPS to AWS APIs (ECR, Secrets Manager, S3, CloudWatch, SSM) and OS packages"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}

resource "aws_vpc_security_group_egress_rule" "app_to_db" {
  security_group_id            = aws_security_group.app.id
  description                  = "PostgreSQL to RDS"
  referenced_security_group_id = aws_security_group.db.id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
}

# --- sg-db (no egress rules: RDS starts no connections) ---

resource "aws_vpc_security_group_ingress_rule" "db_from_app" {
  security_group_id            = aws_security_group.db.id
  description                  = "PostgreSQL from the app instances only"
  referenced_security_group_id = aws_security_group.app.id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
}

# The VPC's built-in default group lets its members talk freely. Adopt it and leave it with no rules,
# so anything accidentally attached to it can reach nothing.
resource "aws_default_security_group" "default" {
  vpc_id = aws_vpc.main.id

  tags = { Name = "${local.name_prefix}-sg-default-deny" }
}
