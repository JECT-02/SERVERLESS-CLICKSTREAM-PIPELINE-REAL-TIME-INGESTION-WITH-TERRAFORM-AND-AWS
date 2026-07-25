provider "aws" {
  region                      = var.aws_region
  access_key                  = var.aws_access_key
  secret_key                  = var.aws_secret_key
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
  }
}

locals {
  common_tags = {
    Environment = var.environment
    Project     = "clickstream"
    ManagedBy   = "terraform"
  }
}

module "s3_bucket" {
  source        = "../../modules/s3-bucket"
  bucket_name   = var.bucket_name
  versioning    = true
  tags          = local.common_tags
}

module "dynamodb_table" {
  source        = "../../modules/dynamodb-table"
  table_name    = var.dynamodb_table_name
  ttl_attribute = "ttl"
  tags          = local.common_tags
}

module "iam_roles" {
  source                   = "../../modules/iam-roles"
  lambda_function_name     = var.lambda_function_name
  ecs_task_name            = var.ecs_task_name
  bucket_arn               = module.s3_bucket.bucket_arn
  dynamodb_table_arn       = module.dynamodb_table.table_arn
  ecs_cluster_arn          = module.ecs_cluster.cluster_arn
  tags                     = local.common_tags
}

module "ecs_cluster" {
  source       = "../../modules/ecs-fargate/cluster"
  cluster_name = var.ecs_cluster_name
  tags         = local.common_tags
}

module "ecr_repo" {
  source       = "../../modules/ecr-repo"
  repo_name    = "clickstream-inference"
  tags         = local.common_tags
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
  tags                = local.common_tags
}

module "alb" {
  source                 = "../../modules/ecs-fargate/alb"
  alb_name               = var.alb_name
  vpc_id                 = var.vpc_id
  subnet_ids             = var.subnet_ids
  security_group_ids     = var.alb_security_group_ids
  target_group_name      = var.target_group_name
  container_port         = var.ecs_container_port
  tags                   = local.common_tags
}

module "ecs_service" {
  source              = "../../modules/ecs-fargate/service"
  cluster_name        = var.ecs_cluster_name
  service_name        = var.ecs_service_name
  task_definition_arn = module.ecs_task_definition.task_definition_arn
  desired_count       = var.ecs_desired_count
  alb_target_group_arn = module.alb.target_group_arn
  subnet_ids          = var.subnet_ids
  security_group_ids  = var.alb_security_group_ids
  tags                = local.common_tags
}

module "lambda_function" {
  source                  = "../../modules/lambda-function"
  function_name           = var.lambda_function_name
  handler                 = var.lambda_handler
  runtime                 = var.lambda_runtime
  timeout                 = var.lambda_timeout
  memory_size             = var.lambda_memory
  env_vars                = var.lambda_env_vars
  role_arn                = module.iam_roles.lambda_execution_role_arn
  source_code_filename    = var.lambda_source_code_filename
  source_code_hash        = var.lambda_source_code_hash
  api_gateway_execution_arn = module.api_gateway.execution_arn
  tags                    = local.common_tags
}

module "api_gateway" {
  source           = "../../modules/api-gateway"
  api_name         = var.api_gateway_name
  lambda_function_arn = module.lambda_function.function_arn
  lambda_invoke_arn  = module.lambda_function.invoke_arn
  stage_name       = "prod"
  tags             = local.common_tags
}

resource "null_resource" "frontend_config" {
  triggers = {
    api_endpoint = module.api_gateway.invoke_url
  }

  provisioner "local-exec" {
    command = <<-EOT
      cat > ${path.module}/../../../frontend/config.js <<'EOF'
window.CLICKSTREAM_CONFIG = {
  apiUrl: "${module.api_gateway.invoke_url}/events",
  trackedPages: ["cart", "checkout"],
  heartbeatIntervalMs: 250
};
EOF
    EOT
  }
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

output "ecs_service_name" {
  value = module.ecs_service.service_name
}

output "alb_dns_name" {
  value = module.alb.alb_dns_name
}