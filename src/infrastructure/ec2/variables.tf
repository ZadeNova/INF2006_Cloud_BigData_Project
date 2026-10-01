variable "region" {
  description = "AWS region. The Learner Lab only offers us-east-1; production would use ap-southeast-1."
  type        = string
  default     = "us-east-1"
}

variable "image_tag" {
  description = "Release tag of the app image in ECR (release-<git-sha>). scripts/push-image.sh writes it to image.auto.tfvars. Terraform resolves it to the immutable digest, so every instance runs the same bytes."
  type        = string
}

variable "instance_type" {
  description = "App instance type (ADR-007). c5.large: 2 vCPU, 4 GiB, non-burstable, matched to Fargate 2 vCPU / 4 GB. Use c5a.large or m5.large if the lab refuses it, and say so in the results."
  type        = string
  default     = "c5.large"
}
