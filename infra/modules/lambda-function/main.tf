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

resource "aws_lambda_permission" "api_gateway_invoke" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingestion.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = var.api_gateway_execution_arn
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