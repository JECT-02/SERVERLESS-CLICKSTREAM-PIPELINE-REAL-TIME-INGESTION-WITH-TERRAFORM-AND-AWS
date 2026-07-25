variable "bucket_name" {
  type        = string
  default     = "clickstream-bucket"
}

variable "versioning_enabled" {
  type        = bool
  default     = true
}

variable "tags" {
  type        = map(string)
  default     = {}
}