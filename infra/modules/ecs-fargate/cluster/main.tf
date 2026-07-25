resource "aws_ecs_cluster" "clickstream" {
  name = var.cluster_name
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
  tags = { Environment = var.environment }
}

output "cluster_arn" {
  value = aws_ecs_cluster.clickstream.arn
}

output "cluster_name" {
  value = aws_ecs_cluster.clickstream.name
}