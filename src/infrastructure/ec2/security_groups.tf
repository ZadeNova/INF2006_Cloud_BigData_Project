# The chain: internet -> sg-alb (443/80) -> sg-app (8000) -> sg-db (5432). No port 22 anywhere.
# Rules are separate resources so sg-alb and sg-app can reference each other without a creation cycle.
# sg-db lives in base/; this stack adds its own rule to it, so base/ never refers to a stack (ADR-001).

resource "aws_security_group" "alb" {
  name        = "${local.stack_prefix}-sg-alb"
  description = "ALB: HTTPS and HTTP-redirect from the internet"
  vpc_id      = local.base.vpc_id

  tags = { Name = "${local.stack_prefix}-sg-alb" }
}

resource "aws_security_group" "app" {
  name        = "${local.stack_prefix}-sg-app"
  description = "App instances: port 8000 from the ALB only"
  vpc_id      = local.base.vpc_id

  tags = { Name = "${local.stack_prefix}-sg-app" }
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

resource "aws_vpc_security_group_ingress_rule" "app_from_alb" {
  security_group_id            = aws_security_group.app.id
  description                  = "Gunicorn, from the ALB only"
  referenced_security_group_id = aws_security_group.alb.id
  ip_protocol                  = "tcp"
  from_port                    = 8000
  to_port                      = 8000
}

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
  referenced_security_group_id = local.base.sg_db_id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
}

# --- sg-db (owned by base/): this stack's own way in ---

resource "aws_vpc_security_group_ingress_rule" "db_from_app" {
  security_group_id            = local.base.sg_db_id
  description                  = "PostgreSQL from the ec2 stack app instances"
  referenced_security_group_id = aws_security_group.app.id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
}
