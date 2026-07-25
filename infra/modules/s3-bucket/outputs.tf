output "bucket_id" {
  value = aws_s3_bucket.clickstream.id
}

output "bucket_arn" {
  value = aws_s3_bucket.clickstream.arn
}

output "bucket_name" {
  value = aws_s3_bucket.clickstream.bucket
}
