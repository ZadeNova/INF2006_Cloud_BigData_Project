variable "region" {
  description = "AWS region. The Learner Lab only offers us-east-1; production would use ap-southeast-1."
  type        = string
  default     = "us-east-1"
}
