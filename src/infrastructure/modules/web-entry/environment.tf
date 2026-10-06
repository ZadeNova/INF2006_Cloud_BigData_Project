# The application's non-secret settings, written once for both variants (ADR-014): the EC2 user data writes them to
# /etc/inf2006/app.env and the Fargate task definition passes them as container environment. The one setting that
# depends on where the app runs, DJANGO_HEALTH_PROBE_HOST (the target's own private IP), is added by each stack's
# compute at start-up. Secrets are never here; the app fetches its own with the compute's role.

locals {
  app_environment = {
    DJANGO_ENV                  = "production"
    AWS_REGION                  = var.region
    APP_RELEASE_ID              = var.release_id
    DJANGO_ALLOWED_HOSTS        = var.hostname
    DJANGO_CSRF_TRUSTED_ORIGINS = "https://${var.hostname}"
    DJANGO_TRUST_PROXY          = "true" # behind the ALB; "false" here would redirect-loop with SECURE_SSL_REDIRECT
    DJANGO_HSTS_SECONDS         = "3600"
  }
}
