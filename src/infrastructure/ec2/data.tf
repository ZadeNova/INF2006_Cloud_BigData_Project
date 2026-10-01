# Everything this stack reads but does not create. base/ owns the shared infrastructure (ADR-001).

# base/'s outputs: the VPC, subnets, sg-db, zone, certificate, registry name and the hostname for this stack.
data "terraform_remote_state" "base" {
  backend = "local"
  config = {
    path = "${path.module}/../base/terraform.tfstate"
  }
}

locals {
  base         = data.terraform_remote_state.base.outputs
  app_hostname = local.base.shop_hostnames["ec2"]
}

# Amazon Linux 2023 for x86_64, from AWS's public SSM parameter. It always points at the newest release: when AWS
# publishes one, the next plan shows a new launch template version. Running instances keep the old AMI until an
# instance refresh (known drift, stated in the write-up).
data "aws_ssm_parameter" "al2023_ami" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

# The lab's instance profile (wraps LabRole). The lab denies creating IAM roles, so instances use this.
data "aws_iam_instance_profile" "lab" {
  name = "LabInstanceProfile"
}

# The app image, looked up by its release tag. Instances run it by digest (sha256:...), never by tag.
data "aws_ecr_image" "app" {
  repository_name = local.base.ecr_repository_name
  image_tag       = var.image_tag
}

# The provider's default tags do not reach instances an ASG launches, so the launch template adds them.
data "aws_default_tags" "current" {}
