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
    ec2           = var.floci_endpoint
    elbv2         = var.floci_endpoint
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

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

data "aws_subnet" "default" {
  count = length(data.aws_subnets.default.ids)
  id    = data.aws_subnets.default.ids[count.index]
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

resource "aws_security_group" "ecs_tasks" {
  name        = var.ecs_sg_name
  description = "Security group for ECS Fargate tasks"
  vpc_id      = data.aws_vpc.default.id
  tags        = local.common_tags
}

resource "aws_security_group_rule" "ecs_tasks_ingress" {
  type              = "ingress"
  from_port         = var.ecs_container_port
  to_port           = var.ecs_container_port
  protocol          = "tcp"
  cidr_blocks       = [data.aws_vpc.default.cidr_block]
  security_group_id = aws_security_group.ecs_tasks.id
}

resource "aws_security_group_rule" "ecs_tasks_egress" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.ecs_tasks.id
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
  image               = "localhost:5100/clickstream-inference:latest"
  cpu                 = var.ecs_cpu
  memory              = var.ecs_memory
  container_port      = var.ecs_container_port
  env_vars            = merge(var.ecs_env_vars, {
    AWS_ENDPOINT_URL     = "http://host.docker.internal:4566"
    AWS_ACCESS_KEY_ID    = "test"
    AWS_SECRET_ACCESS_KEY = "test"
    AWS_DEFAULT_REGION   = "us-east-1"
  })
  task_execution_role = module.iam_roles.ecs_task_execution_role_arn
}

resource "aws_security_group" "alb" {
  name        = "clickstream-alb-sg"
  description = "Security group for clickstream ALB"
  vpc_id      = data.aws_vpc.default.id
  tags        = local.common_tags
}

resource "aws_security_group_rule" "alb_ingress" {
  type              = "ingress"
  from_port         = 80
  to_port           = 80
  protocol          = "tcp"
  cidr_blocks       = ["10.0.0.0/16"]
  security_group_id = aws_security_group.alb.id
}

resource "aws_security_group_rule" "alb_egress" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.alb.id
}

module "alb" {
  source             = "../../modules/ecs-fargate/alb"
  alb_name           = "clickstream-alb"
  vpc_id             = data.aws_vpc.default.id
  subnet_ids         = data.aws_subnets.default.ids
  security_group_ids = [aws_security_group.alb.id]
  target_group_name  = "clickstream-tg"
  container_port     = var.ecs_container_port
  tags               = local.common_tags
}

module "ecs_service" {
  source               = "../../modules/ecs-fargate/service"
  cluster_name         = module.ecs_cluster.cluster_name
  service_name         = var.ecs_service_name
  task_definition_arn  = module.ecs_task_definition.task_definition_arn
  desired_count        = var.ecs_desired_count
  alb_target_group_arn = module.alb.target_group_arn
  subnet_ids           = data.aws_subnets.default.ids
  security_group_ids   = [aws_security_group.ecs_tasks.id]
}

module "lambda_function" {
  source                    = "../../modules/lambda-function"
  function_name             = var.lambda_function_name
  handler                   = var.lambda_handler
  runtime                   = var.lambda_runtime
  timeout                   = var.lambda_timeout
  memory_size               = var.lambda_memory
  environment_variables     = merge(var.lambda_env_vars, {
    ECS_ENDPOINT = "http://${module.alb.alb_dns_name}:80"
  })
  role_arn                  = module.iam_roles.lambda_execution_role_arn
  source_code_filename      = var.lambda_source_code_filename
  source_code_hash          = local.lambda_source_code_hash
}

module "api_gateway" {
  source             = "../../modules/api-gateway"
  api_name           = var.api_gateway_name
  lambda_function_arn = module.lambda_function.function_arn
  lambda_invoke_arn  = module.lambda_function.invoke_arn
  stage_name         = "prod"
}

resource "aws_lambda_permission" "api_gateway_invoke" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = module.lambda_function.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = module.api_gateway.execution_arn
}

resource "local_file" "api_id" {
  filename = "${path.module}/../../../frontend/.api_id"
  content  = module.api_gateway.rest_api_id
}

resource "local_file" "frontend_config" {
  filename = "${path.module}/../../../frontend/config.js"
  content  = <<-EOF
window.CLICKSTREAM_CONFIG = {
  apiUrl: "http://localhost:8000/api/events",
  trackedPages: ["cart", "checkout"],
  heartbeatIntervalMs: 250
};
EOF
  depends_on = [local_file.api_id]
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

output "vpc_id" {
  value = data.aws_vpc.default.id
}

output "public_subnet_ids" {
  value = data.aws_subnets.default.ids
}

output "ecs_tasks_security_group_id" {
  value = aws_security_group.ecs_tasks.id
}