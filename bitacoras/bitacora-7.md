# Bitacora 7 - Modulo VPC para ECS Fargate
**Proyecto:** Serverless Clickstream Pipeline - Real-Time Event Ingestion with Terraform & Polars

## Cambios Realizados

### Modulo VPC (`infra/modules/vpc/`)

| Recurso | Detalle |
|---------|---------|
| VPC | `10.0.0.0/16`, DNS support + hostnames enabled |
| 2 subnets publicas | `10.0.1.0/24` (us-east-1a), `10.0.2.0/24` (us-east-1b) |
| Internet Gateway | Para trafico saliente desde subnets publicas |
| Route table publica | `0.0.0.0/0` -> IGW |
| SG `clickstream-ecs-tasks-sg` | Ingress: puerto 8080 desde VPC CIDR. Egress: all traffic |

Disenado para ECS Fargate. Se crea en Floci (EC2 soportado).

### local/main.tf

- `ec2` endpoint agregado al provider de Floci
- `module "vpc"` agregado usando `local.common_tags`
- Outputs: `vpc_id`, `public_subnet_ids`, `ecs_tasks_security_group_id`

### Outputs duplicados corregidos

Existian outputs duplicados en `main.tf` y `outputs.tf`:
- `api-gateway`: consolidado en `outputs.tf`
- `dynamodb-table`: consolidado en `outputs.tf`
- `s3-bucket`: consolidado en `outputs.tf`, se agrego `bucket_name`

### Floci ECS task definition fix

`cpu` y `memory` removidos del bloque `container_definitions` porque Floci falla con strings en esos campos (espera int32 y recibe string).

## Resultados

### Terraform Apply en Floci
```
Apply complete! Resources: 6 added, 7 changed, 14 destroyed.
```
VPC `vpc-29c71489` (10.0.0.0/16) creado exitosamente.

### Integration tests: 13/13 pasando
Post-apply verificado que todo el pipeline de ingestion sigue funcionando.

## Commit
```
1d34d91 feat: add VPC module for ECS Fargate networking
```

## Notas para AWS Real
- Cambiar provider endpoint de `localhost:4566` a `us-east-1` de AWS real
- Agregar modulo `alb` (`infra/modules/ecs-fargate/alb/`) y `ecs-fargate/service/` en `environments/aws/main.tf`
- Asignar Lambda a la VPC para que alcance el ALB interno
- Floci no soporta ELBv2, por eso ALB y ECS Service no se incluyen en `local/`