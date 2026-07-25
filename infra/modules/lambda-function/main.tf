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

  dynamic "vpc_config" {
    for_each = length(var.vpc_subnet_ids) > 0 ? [1] : []
    content {
      subnet_ids         = var.vpc_subnet_ids
      security_group_ids = var.vpc_security_group_ids
    }
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