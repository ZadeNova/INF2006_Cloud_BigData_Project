provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project   = "inf2006"
      Env       = "evidence"
      ManagedBy = "terraform"
    }
  }
}
