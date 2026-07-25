output "bucket_id" {
  value = aws_s3_bucket.clickstream.id
}

output "bucket_name" {
  value = aws_s3_bucket.clickstream.bucket
}

output "bucket_arn" {
  value = aws_s3_bucket.clickstream.arn
}