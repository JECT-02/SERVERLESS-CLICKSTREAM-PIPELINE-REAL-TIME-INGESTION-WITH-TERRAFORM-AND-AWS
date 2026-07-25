variable "family" {
  type        = string
}

variable "container_name" {
  type        = string
}

variable "image" {
  type        = string
}

variable "cpu" {
  type        = string
}

variable "memory" {
  type        = string
}

variable "container_port" {
  type        = number
}

variable "env_vars" {
  type        = map(string)
  default     = {}
}

variable "task_execution_role" {
  type        = string
}

variable "environment" {
  type        = string
  default     = "local"
}