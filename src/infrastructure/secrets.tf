# Containers only. No aws_secretsmanager_secret_version here: a value set in Terraform would be
# written into terraform.tfstate in plain text. Values are set with `aws secretsmanager
# put-secret-value` at stage 1 step 8, straight to the API, never through Terraform state.
# Field lists: docs/AWS_INFRASTRUCTURE.md#secrets-manager-startup-and-alb-boundary and
# docs/plans/aws-terraform-stage-1.md.

locals {
  # One secret per job, so a compromised process only ever holds its own credentials.
  secret_jobs = {
    web       = "Unprivileged runtime DB login and the Django signing key, read by every app instance at boot"
    migration = "Migration-owner DB login, read once by the coordinated migration run"
    trainer   = "Read-only DB login for the standalone ML trainer and refresh verifier, no Django signing key"
    bootstrap = "RDS master login plus the migration and runtime credentials it provisions; the one-off db_bootstrap run only"
  }
}

resource "aws_secretsmanager_secret" "app" {
  for_each = local.secret_jobs

  name        = "${local.name_prefix}/${each.key}"
  description = each.value

  # No 30-day pending-deletion hold: the lab stack is destroyed and re-applied more than once
  # before submission, and nothing stored here is worth a recovery window.
  recovery_window_in_days = 0

  tags = { Name = "${local.name_prefix}-secret-${each.key}" }
}
