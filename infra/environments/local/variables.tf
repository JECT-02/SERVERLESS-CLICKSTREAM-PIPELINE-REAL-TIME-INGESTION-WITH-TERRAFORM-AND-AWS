variable "aws_region" {
  type        = string
  default     = "us-east-1"
}

variable "aws_access_key" {
  type        = string
  default     = "test"
}

variable "aws_secret_key" {
  type        = string
  default     = "test"
}

variable "floci_endpoint" {
  type        = string
  default     = "http://localhost:4566"
}

variable "bucket_name" {
  type        = string
  default     = "clickstream-bucket"
}

variable "dynamodb_table_name" {
  type        = string
  default     = "clickstream-sessions"
}

variable "environment" {
  type        = string
  default     = "local"
}

variable "lambda_function_name" {
  type        = string
  default     = "clickstream-ingestion"
}

variable "lambda_handler" {
  type        = string
  default     = "lambda_function.lambda_handler"
}

variable "lambda_runtime" {
  type        = string
  default     = "python3.11"
}

variable "lambda_timeout" {
  type        = number
  default     = 30
}

variable "lambda_memory" {
  type        = number
  default     = 512
}

variable "lambda_env_vars" {
  type        = map(string)
  default     = {
    S3_BUCKET = "clickstream-bucket"
    DYNAMODB_TABLE = "clickstream-sessions"
    AWS_ENDPOINT_URL = "http://localhost:4566"
  }
}

variable "lambda_source_code_filename" {
  type        = string
  default     = ""
}

variable "lambda_source_code_hash" {
  type        = string
  default     = ""
}

variable "api_gateway_name" {
  type        = string
  default     = "clickstream-api"
}

variable "ecs_cluster_name" {
  type        = string
  default     = "clickstream-cluster"
}

variable "ecs_task_name" {
  type        = string
  default     = "clickstream-inference"
}

variable "ecs_task_family" {
  type        = string
  default     = "clickstream-inference"
}

variable "ecs_container_name" {
  type        = string
  default     = "inference"
}

variable "ecs_image" {
  type        = string
  default     = "clickstream-inference:latest"
}

variable "ecs_cpu" {
  type        = string
  default     = "512"
}

variable "ecs_memory" {
  type        = string
  default     = "1024"
}

variable "ecs_container_port" {
  type        = number
  default     = 8080
}

variable "ecs_env_vars" {
  type        = map(string)
  default     = {}
}

variable "ecs_service_name" {
  type        = string
  default     = "clickstream-inference-service"
}

variable "ecs_desired_count" {
  type        = number
  default     = 1
}

variable "vpc_id" {
  type        = string
  default     = ""
}

variable "subnet_ids" {
  type        = list(string)
  default     = []
}

variable "alb_security_group_ids" {
  type        = list(string)
  default     = []
}

variable "alb_name" {
  type        = string
  default     = "clickstream-alb"
}

variable "target_group_name" {
  type        = string
  default     = "clickstream-tg"
}