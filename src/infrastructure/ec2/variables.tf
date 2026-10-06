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

variable "scale_target_requests" {
  description = "ADR-011: target tracking keeps the average requests per instance per minute near this value. Starting point; tune from the load rehearsal. Low enough that the load test can trigger scale-out."
  type        = number
  default     = 300
}

variable "waf_login_limit" {
  description = "ADR-012: requests allowed per IP per 5 minutes to POST /login/ before the WAF rule acts (minimum 10). A person logging in does not reach 20; credential stuffing does."
  type        = number
  default     = 20
}

variable "waf_login_action" {
  description = "ADR-012: count (record only) or block (reject with 403). Starts at count so the rule is observed before it can lock anyone out; set block for the security test."
  type        = string
  default     = "count"

  validation {
    condition     = contains(["count", "block"], var.waf_login_action)
    error_message = "waf_login_action must be count or block."
  }
}

# ADR-013: capacity pinning for fixed-capacity load runs. Defaults are the ADR-011 values (1 to 2, starting at 1).
# Pin by setting all three to the same number (for example 2), apply, and unpin the same way afterwards. Applying
# also resets a desired capacity that scaling has moved, so the group starts a run where the variables say.
variable "min_capacity" {
  description = "Smallest number of instances the Auto Scaling group keeps (fargate/ uses the same variable names for tasks)."
  type        = number
  default     = 1

  validation {
    condition     = var.min_capacity >= 1
    error_message = "min_capacity must be at least 1."
  }
}

variable "max_capacity" {
  description = "Largest number of instances scaling may add. Keep it small: it caps the cost of a runaway load test."
  type        = number
  default     = 2

  validation {
    condition     = var.max_capacity >= var.min_capacity
    error_message = "max_capacity must be at least min_capacity."
  }
}

variable "desired_capacity" {
  description = "Instances wanted when the group is created or this stack is applied."
  type        = number
  default     = 1

  validation {
    condition     = var.desired_capacity >= var.min_capacity && var.desired_capacity <= var.max_capacity
    error_message = "desired_capacity must be between min_capacity and max_capacity."
  }
}
