resource "aws_lambda_function" "ingestion" {
  function_name = var.function_name
  role          = var.role_arn
  handler       = var.handler
  runtime       = var.runtime
  timeout       = var.timeout
  memory_size   = var.memory_size
  filename      = var.source_code_filename != "" ? var.source_code_filename : null
  source_code_hash = var.source_code_hash != "" ? var.source_code_hash : null

  environment {
    variables = var.environment_variables
  }
}

output "function_arn" {
  value = aws_lambda_function.ingestion.arn
}

output "function_name" {
  value = aws_lambda_function.ingestion.function_name
}

output "invoke_arn" {
  value = aws_lambda_function.ingestion.invoke_arn
}