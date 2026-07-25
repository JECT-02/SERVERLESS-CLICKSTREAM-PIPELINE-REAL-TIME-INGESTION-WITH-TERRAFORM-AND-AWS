resource "aws_dynamodb_table" "sessions" {
  name           = var.table_name
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "session_id"
  range_key      = "timestamp"
  ttl {
    attribute_name = var.ttl_attribute
    enabled        = true
  }
  attribute {
    name = "session_id"
    type = "S"
  }
  attribute {
    name = "timestamp"
    type = "N"
  }
  tags = var.tags
}

output "table_name" {
  value = aws_dynamodb_table.sessions.name
}

output "table_arn" {
  value = aws_dynamodb_table.sessions.arn
}