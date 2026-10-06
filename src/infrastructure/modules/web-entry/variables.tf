variable "name" {
  description = "Prefix for every resource name in this module, for example inf2006-grp21-ec2. Unique per stack."
  type        = string
}

variable "stack" {
  description = "Stack key (ec2 or fargate), used in descriptions."
  type        = string
}

variable "region" {
  description = "AWS region, passed on to the app as AWS_REGION."
  type        = string
}

variable "hostname" {
  description = "The HTTPS hostname this stack serves (from base/shop_hostnames)."
  type        = string
}

variable "target_type" {
  description = "How the load balancer reaches the app: instance (Auto Scaling group) or ip (Fargate, awsvpc)."
  type        = string

  validation {
    condition     = contains(["instance", "ip"], var.target_type)
    error_message = "target_type must be instance or ip."
  }
}

variable "release_id" {
  description = "Release tag of the running image, passed on to the app as APP_RELEASE_ID."
  type        = string
}

# --- from base/ ---

variable "vpc_id" {
  type = string
}

variable "public_subnet_ids" {
  description = "Public subnet IDs: the ALB sits in all of them."
  type        = list(string)
}

variable "sg_db_id" {
  description = "sg-db from base/. The module adds this stack's own rule on it."
  type        = string
}

variable "certificate_arn" {
  type = string
}

variable "zone_id" {
  description = "Route 53 hosted zone for the alias record."
  type        = string
}

variable "sns_topic_arn" {
  description = "Topic the alarms email."
  type        = string
}

# --- ADR-012 ---

variable "waf_login_limit" {
  description = "Requests allowed per IP per 5 minutes to POST /login/ before the WAF rule acts (minimum 10)."
  type        = number
}

variable "waf_login_action" {
  description = "count (record only) or block (reject with 403)."
  type        = string

  validation {
    condition     = contains(["count", "block"], var.waf_login_action)
    error_message = "waf_login_action must be count or block."
  }
}
