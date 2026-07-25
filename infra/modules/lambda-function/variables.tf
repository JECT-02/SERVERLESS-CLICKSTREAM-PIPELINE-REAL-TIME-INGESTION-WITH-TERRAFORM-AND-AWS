variable "function_name" {
  type        = string
  default     = "clickstream-ingestion"
}

variable "handler" {
  type        = string
  default     = "lambda_function.lambda_handler"
}

variable "runtime" {
  type        = string
  default     = "python3.11"
}

variable "timeout" {
  type        = number
  default     = 30
}

variable "memory_size" {
  type        = number
  default     = 512
}

variable "environment_variables" {
  type        = map(string)
  default     = {}
}

variable "role_arn" {
  type        = string
}

variable "source_code_filename" {
  type        = string
  default     = ""
}

variable "source_code_hash" {
  type        = string
  default     = ""
}

variable "api_gateway_execution_arn" {
  type        = string
  default     = ""
}