# Things Terraform reads but never creates.

# Amazon Linux 2023 for x86_64 (t3 instances), from AWS's public SSM parameter. It always points at the
# newest AL2023 release: when AWS publishes one, the next plan shows a new launch template version.
# Running instances are not replaced until the ASG replaces them, so read that plan line and decide.
data "aws_ssm_parameter" "al2023_ami" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

# The lab's instance profile (wraps LabRole). The lab denies creating IAM roles, so instances use this.
data "aws_iam_instance_profile" "lab" {
  name = "LabInstanceProfile"
}

# The app image to run, looked up by its git-SHA tag. Instances run it by digest (sha256:...), so an
# instance launched later runs exactly the same bytes, even if tags were ever misused.
data "aws_ecr_image" "app" {
  repository_name = aws_ecr_repository.app.name
  image_tag       = var.image_tag
}

# The provider's default tags (Project, Env, ManagedBy). They do not reach instances an ASG launches,
# so the launch template adds them explicitly.
data "aws_default_tags" "current" {}
