locals {
  name_prefix  = "inf2006-grp21"         # same group prefix as base/ and the stacks
  stack_prefix = "inf2006-grp21-loadgen" # this stack's own resources (ADR-001, ADR-013)
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project   = local.name_prefix
      Env       = "evidence"
      ManagedBy = "terraform"
      Stack     = "loadgen" # ADR-013
    }
  }
}
