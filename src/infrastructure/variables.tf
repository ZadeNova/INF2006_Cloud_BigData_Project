variable "region" {
  description = "AWS region. The Learner Lab only offers us-east-1; production would use ap-southeast-1."
  type        = string
  default     = "us-east-1"
}

variable "availability_zones" {
  description = "Two AZs for the ALB and the RDS subnet group (both require at least two)."
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "app_hostname" {
  description = "Public HTTPS hostname of the shop (for example shop.example.xyz); used for the certificate, DJANGO_ALLOWED_HOSTS and the CSRF trusted origin."
  type        = string
  default     = null
}

variable "alarm_email" {
  description = "Address subscribed to the SNS alarm topic. AWS emails a subscription-confirmation link once this is applied; the subscription stays pending until it's clicked."
  type        = string
}

variable "s3_bucket_name" {
  description = "Name of the S3 bucket created with the CLI (the lab denies a read the aws_s3_bucket resource needs). Must start with the name prefix, e.g. inf2006-grp21-data-<suffix>."
  type        = string
}

variable "db_instance_class" {
  description = "RDS instance class. db.t4g.micro is the smallest current burstable class; use db.t3.micro if the lab refuses it."
  type        = string
  default     = "db.t4g.micro"
}

variable "image_tag" {
  description = "Release tag of the app image in ECR to deploy (release-<git-sha>, protected from lifecycle expiry). Terraform resolves it to the immutable digest."
  type        = string
}

variable "instance_type" {
  description = "App instance type. t3.small: 2 vCPU, 2 GiB, enough for Gunicorn with 2 workers."
  type        = string
  default     = "t3.small"
}
