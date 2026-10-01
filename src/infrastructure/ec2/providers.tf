locals {
  # Every resource name and tag is built from these, so the group number changes in one place.
  name_prefix  = "inf2006-grp21"     # shared names: the secrets, the database, the registry (all in base/)
  stack_prefix = "inf2006-grp21-ec2" # this stack's own resources (ADR-001)
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project   = local.name_prefix
      Env       = "evidence"
      ManagedBy = "terraform"
      Stack     = "ec2" # ADR-001
    }
  }
}
