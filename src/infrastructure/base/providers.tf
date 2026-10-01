locals {
  # Every resource name and tag is built from this, so the group number changes in one place.
  name_prefix = "inf2006-grp21"
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project   = local.name_prefix
      Env       = "evidence"
      ManagedBy = "terraform"
    }
  }
}
