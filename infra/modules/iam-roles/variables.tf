variable "lambda_function_name" {
  type        = string
  default     = "clickstream-ingestion"
}

variable "ecs_task_name" {
  type        = string
  default     = "clickstream-inference"
}

variable "bucket_arn" {
  type        = string
}

variable "dynamodb_table_arn" {
  type        = string
}

variable "ecs_cluster_arn" {
  type        = string
}