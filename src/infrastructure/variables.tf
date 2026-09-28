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
  description = "Public HTTPS hostname of the shop (for example shop.example.xyz). Null until the domain exists; S3 CORS is only created once it is set."
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
