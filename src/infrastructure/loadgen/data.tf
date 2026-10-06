# Everything this stack reads but does not create. base/ owns the network (ADR-001).

data "terraform_remote_state" "base" {
  backend = "local"
  config = {
    path = "${path.module}/../base/terraform.tfstate"
  }
}

locals {
  base = data.terraform_remote_state.base.outputs
}

# Amazon Linux 2023, x86_64, newest release (same source as ec2/).
data "aws_ssm_parameter" "al2023_ami" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

# The lab's instance profile (wraps LabRole): Session Manager to get a shell, and S3 to move the harness and results.
data "aws_iam_instance_profile" "lab" {
  name = "LabInstanceProfile"
}
