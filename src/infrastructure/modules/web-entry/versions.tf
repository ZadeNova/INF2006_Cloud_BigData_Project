terraform {
  required_version = ">= 1.10, < 2.0"

  # Providers are configured by the calling stack (region, default tags); the module only says which one it needs.
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}
