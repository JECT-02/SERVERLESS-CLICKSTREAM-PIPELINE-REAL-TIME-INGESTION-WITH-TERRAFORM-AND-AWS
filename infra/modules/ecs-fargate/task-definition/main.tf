resource "aws_ecs_task_definition" "inference" {
  family                   = var.family
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = var.task_execution_role

  container_definitions = jsonencode([{
    name        = var.container_name
    image       = var.image
    cpu         = var.cpu
    memory      = var.memory
    portMappings = [{
      containerPort = var.container_port
      protocol      = "tcp"
    }]
    environment = [
      for k, v in var.env_vars : {
        name  = k
        value = v
      }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = "/ecs/${var.family}"
        "awslogs-region"        = "us-east-1"
        "awslogs-stream-prefix" = "ecs"
      }
    }
    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:8080/health || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
  }])

  tags = { Environment = var.environment }
}

output "task_definition_arn" {
  value = aws_ecs_task_definition.inference.arn
}