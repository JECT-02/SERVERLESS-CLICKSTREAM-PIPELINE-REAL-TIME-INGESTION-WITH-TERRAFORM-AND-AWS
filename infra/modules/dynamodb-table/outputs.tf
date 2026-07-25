output "table_name" {
  value = aws_dynamodb_table.sessions.name
}

output "table_arn" {
  value = aws_dynamodb_table.sessions.arn
}

output "table_hash_key" {
  value = aws_dynamodb_table.sessions.hash_key
}

output "table_range_key" {
  value = aws_dynamodb_table.sessions.range_key
}