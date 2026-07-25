provider "aws" {
  region                      = var.aws_region
  access_key                  = var.aws_access_key
  secret_key                  = var.aws_secret_key
  s3_use_path_style           = true
  endpoints {
    s3            = var.floci_endpoint
    lambda        = var.floci_endpoint
    dynamodb      = var.floci_endpoint
    apigateway    = var.floci_endpoint
    ecs           = var.floci_endpoint
    ecr           = var.floci_endpoint
    iam           = var.floci_endpoint
    logs          = var.floci_endpoint
    cloudformation = var.floci_endpoint
  }
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
}

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.4"
    }
  }
}

locals {
  common_tags = {
    Environment = var.environment
    Project     = "clickstream"
    ManagedBy   = "terraform"
  }
  lambda_source_code_hash = filebase64sha256(var.lambda_source_code_filename)
}

module "s3_bucket" {
  source             = "../../modules/s3-bucket"
  bucket_name        = var.bucket_name
  versioning_enabled = true
  tags               = local.common_tags
}

module "dynamodb_table" {
  source        = "../../modules/dynamodb-table"
  table_name    = var.dynamodb_table_name
  ttl_attribute = "ttl"
}

module "iam_roles" {
  source               = "../../modules/iam-roles"
  lambda_function_name = var.lambda_function_name
  ecs_task_name        = var.ecs_task_name
  bucket_arn           = module.s3_bucket.bucket_arn
  dynamodb_table_arn   = module.dynamodb_table.table_arn
  ecs_cluster_arn      = ""
}

module "ecs_cluster" {
  source       = "../../modules/ecs-fargate/cluster"
  cluster_name = var.ecs_cluster_name
}

module "ecr_repo" {
  source    = "../../modules/ecr-repo"
  repo_name = "clickstream-inference"
}

module "ecs_task_definition" {
  source              = "../../modules/ecs-fargate/task-definition"
  family              = var.ecs_task_family
  container_name      = var.ecs_container_name
  image               = var.ecs_image
  cpu                 = var.ecs_cpu
  memory              = var.ecs_memory
  container_port      = var.ecs_container_port
  env_vars            = var.ecs_env_vars
  task_execution_role = module.iam_roles.ecs_task_execution_role_arn
}

module "lambda_function" {
  source                    = "../../modules/lambda-function"
  function_name             = var.lambda_function_name
  handler                   = var.lambda_handler
  runtime                   = var.lambda_runtime
  timeout                   = var.lambda_timeout
  memory_size               = var.lambda_memory
  environment_variables     = var.lambda_env_vars
  role_arn                  = module.iam_roles.lambda_execution_role_arn
  source_code_filename      = var.lambda_source_code_filename
  source_code_hash          = local.lambda_source_code_hash
  api_gateway_execution_arn = module.api_gateway.execution_arn
}

module "api_gateway" {
  source             = "../../modules/api-gateway"
  api_name           = var.api_gateway_name
  lambda_function_arn = module.lambda_function.function_arn
  lambda_invoke_arn  = module.lambda_function.invoke_arn
  stage_name         = "prod"
}

resource "local_file" "frontend_config" {
  filename = "${path.module}/../../../frontend/config.js"
  content  = <<-EOF
window.CLICKSTREAM_CONFIG = {
  apiUrl: "http://localhost:4566/restapis/${module.api_gateway.rest_api_id}/prod/_user_request_/events",
  trackedPages: ["cart", "checkout"],
  heartbeatIntervalMs: 250
};
EOF
}

output "api_gateway_url" {
  value = module.api_gateway.invoke_url
}

output "s3_bucket_name" {
  value = module.s3_bucket.bucket_name
}

output "dynamodb_table_name" {
  value = module.dynamodb_table.table_name
}

output "lambda_function_name" {
  value = module.lambda_function.function_name
}