output "rest_api_id" {
  value = aws_api_gateway_rest_api.api.id
}

output "stage_name" {
  value = aws_api_gateway_stage.stage.stage_name
}

output "invoke_url" {
  value = aws_api_gateway_stage.stage.invoke_url
}