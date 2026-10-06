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
  app_hostname = local.base.shop_hostnames["fargate"]
}

# The lab's role (the lab denies creating IAM roles). It is both the execution role (pulls the image, writes logs) and
# the task role (the app reads Secrets Manager with it): config/secrets.py accepts it as the container-role source.
data "aws_iam_role" "lab" {
  name = "LabRole"
}

# The app image, looked up by its release tag. Tasks run it by digest (sha256:...), never by tag.
data "aws_ecr_image" "app" {
  repository_name = local.base.ecr_repository_name
  image_tag       = var.image_tag
}
