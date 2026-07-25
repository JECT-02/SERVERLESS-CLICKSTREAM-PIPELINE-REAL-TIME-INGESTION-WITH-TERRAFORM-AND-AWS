variable "cluster_name" {
  type        = string
}

variable "service_name" {
  type        = string
}

variable "task_definition_arn" {
  type        = string
}

variable "desired_count" {
  type        = number
  default     = 1
}

variable "alb_target_group_arn" {
  type        = string
}

variable "subnet_ids" {
  type        = list(string)
}

variable "security_group_ids" {
  type        = list(string)
}

variable "environment" {
  type        = string
  default     = "local"
}