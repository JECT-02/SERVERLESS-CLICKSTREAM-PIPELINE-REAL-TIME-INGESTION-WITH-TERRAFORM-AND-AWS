variable "alb_name" {
  type        = string
  default     = "clickstream-alb"
}

variable "vpc_id" {
  type        = string
  default     = ""
}

variable "subnet_ids" {
  type        = list(string)
  default     = []
}

variable "security_group_ids" {
  type        = list(string)
  default     = []
}

variable "target_group_name" {
  type        = string
  default     = "clickstream-tg"
}

variable "container_port" {
  type        = number
  default     = 8080
}

variable "tags" {
  type        = map(string)
  default     = {}
}