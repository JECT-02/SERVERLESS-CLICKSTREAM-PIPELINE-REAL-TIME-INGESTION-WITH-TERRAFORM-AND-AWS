resource "aws_ecs_service" "inference" {
  name                              = var.service_name
  cluster                           = var.cluster_name
  task_definition                   = var.task_definition_arn
  desired_count                     = var.desired_count
  launch_type                       = "FARGATE"
  platform_version                  = "LATEST"
  network_configuration {
    subnets         = var.subnet_ids
    security_groups = var.security_group_ids
    assign_public_ip = false
  }
  load_balancer {
    target_group_arn = var.alb_target_group_arn
    container_name   = "inference"
    container_port   = 8080
  }
  tags = { Environment = var.environment }
}

output "service_name" {
  value = aws_ecs_service.inference.name
}

output "service_arn" {
  value = aws_ecs_service.inference.arn
}