variable "api_name" {
  type        = string
  default     = "clickstream-api"
}

variable "lambda_function_arn" {
  type        = string
}

variable "lambda_invoke_arn" {
  type        = string
}

variable "stage_name" {
  type        = string
  default     = "prod"
}