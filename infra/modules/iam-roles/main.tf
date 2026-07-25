resource "aws_iam_role" "lambda_execution" {
  name = "${var.lambda_function_name}-execution-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "lambda_s3_write" {
  name = "${var.lambda_function_name}-s3-write"
  role = aws_iam_role.lambda_execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["s3:PutObject", "s3:GetObject"]
      Resource = ["${var.bucket_arn}/raw/*", "${var.bucket_arn}/models/*"]
    }]
  })
}

resource "aws_iam_role_policy" "lambda_dynamodb" {
  name = "${var.lambda_function_name}-dynamodb"
  role = aws_iam_role.lambda_execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["dynamodb:PutItem", "dynamodb:Query", "dynamodb:GetItem"]
      Resource = var.dynamodb_table_arn
    }]
  })
}

resource "aws_iam_role_policy" "lambda_logs" {
  name = "${var.lambda_function_name}-logs"
  role = aws_iam_role.lambda_execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
      Resource = "*"
    }]
  })
}

resource "aws_iam_role" "ecs_task_execution" {
  name = "${var.ecs_task_name}-execution-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "ecs_s3_read" {
  name = "${var.ecs_task_name}-s3-read"
  role = aws_iam_role.ecs_task_execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["s3:GetObject"]
      Resource = "${var.bucket_arn}/models/*"
    }]
  })
}

resource "aws_iam_role_policy" "ecs_logs" {
  name = "${var.ecs_task_name}-logs"
  role = aws_iam_role.ecs_task_execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
      Resource = "*"
    }]
  })
}

output "lambda_execution_role_arn" {
  value = aws_iam_role.lambda_execution.arn
}

output "ecs_task_execution_role_arn" {
  value = aws_iam_role.ecs_task_execution.arn
}