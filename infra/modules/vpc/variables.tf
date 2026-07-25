variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"

}

variable "public_subnet_cidrs" {
  type    = list(string)
  default = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "availability_zones" {
  type    = list(string)
  default = ["us-east-1a", "us-east-1b"]
}

variable "container_port" {
  type    = number
  default = 8080
}

variable "ecs_sg_name" {
  type    = string
  default = "clickstream-ecs-tasks-sg"
}

variable "tags" {
  type    = map(string)
  default = {}
}
