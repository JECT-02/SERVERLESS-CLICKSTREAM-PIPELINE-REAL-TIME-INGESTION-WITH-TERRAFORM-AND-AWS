variable "table_name" {
  type        = string
  default     = "clickstream-sessions"
}

variable "ttl_attribute" {
  type        = string
  default     = "ttl"
}

variable "tags" {
  type        = map(string)
  default     = {}
}