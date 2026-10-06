variable "region" {
  description = "AWS region. The Learner Lab only offers us-east-1; production would use ap-southeast-1."
  type        = string
  default     = "us-east-1"
}

variable "image_tag" {
  description = "Release tag of the app image in ECR (release-<git-sha>). scripts/push-image.sh writes it to image.auto.tfvars. Terraform resolves it to the immutable digest, so every task runs the same bytes, and the same ones the ec2 stack runs."
  type        = string
}

variable "task_cpu" {
  description = "Fargate task CPU units (ADR-015). 2048 = 2 vCPU, matched to the c5.large of the ec2 stack."
  type        = number
  default     = 2048
}

variable "task_memory" {
  description = "Fargate task memory in MiB (ADR-015). 4096 = 4 GB, matched to the c5.large."
  type        = number
  default     = 4096
}

variable "scale_target_requests" {
  description = "ADR-011 and ADR-017: target tracking keeps the average requests per task per minute near this value. The same number as the ec2 stack, so the two scale on the same signal."
  type        = number
  default     = 300
}

variable "waf_login_limit" {
  description = "ADR-012: requests allowed per IP per 5 minutes to POST /login/ before the WAF rule acts (minimum 10)."
  type        = number
  default     = 20
}

variable "waf_login_action" {
  description = "ADR-012: count (record only) or block (reject with 403). Starts at count; set block for the security test."
  type        = string
  default     = "count"

  validation {
    condition     = contains(["count", "block"], var.waf_login_action)
    error_message = "waf_login_action must be count or block."
  }
}

# ADR-013: capacity pinning for fixed-capacity load runs, same names as the ec2 stack (here they count tasks).
# Pin by setting all three to the same number, apply, and unpin the same way afterwards. Applying also resets a task
# count that scaling has moved, so a run starts where the variables say.
variable "min_capacity" {
  description = "Smallest number of tasks scaling keeps."
  type        = number
  default     = 1

  validation {
    condition     = var.min_capacity >= 1
    error_message = "min_capacity must be at least 1."
  }
}

variable "max_capacity" {
  description = "Largest number of tasks scaling may add. Keep it small: it caps the cost of a runaway load test and the Fargate vCPU quota is unknown."
  type        = number
  default     = 2

  validation {
    condition     = var.max_capacity >= var.min_capacity
    error_message = "max_capacity must be at least min_capacity."
  }
}

variable "desired_capacity" {
  description = "Tasks wanted when the service is created or this stack is applied."
  type        = number
  default     = 1

  validation {
    condition     = var.desired_capacity >= var.min_capacity && var.desired_capacity <= var.max_capacity
    error_message = "desired_capacity must be between min_capacity and max_capacity."
  }
}
