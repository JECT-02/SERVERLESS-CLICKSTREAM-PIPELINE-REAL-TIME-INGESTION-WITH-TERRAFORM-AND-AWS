resource "aws_ecr_repository" "inference" {
  name                 = var.repo_name
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }
  tags = { Environment = var.environment }
}

output "repo_url" {
  value = aws_ecr_repository.inference.repository_url
}