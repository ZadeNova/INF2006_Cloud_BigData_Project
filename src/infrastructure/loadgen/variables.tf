variable "region" {
  description = "AWS region. The Learner Lab only offers us-east-1; the load must come from the same region as the app."
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "Generator instance type (ADR-013). c5.large: 2 vCPU, non-burstable, so Locust can run two worker processes at a steady speed and the run is never limited by CPU credits."
  type        = string
  default     = "c5.large"
}
