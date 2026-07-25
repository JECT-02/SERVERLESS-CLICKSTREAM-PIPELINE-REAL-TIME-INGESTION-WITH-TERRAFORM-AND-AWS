# Bitacora 7 - Configuracion de Red VPC para AWS Real y Floci
**Fecha:** 2026-07-25
**Proyecto:** Serverless Clickstream Pipeline - Real-Time Event Ingestion with Terraform & Polars

---

## Cambios Realizados

### 1. Modulo VPC (`infra/modules/vpc/`)

| Recurso | Detalle |
|---------|---------|
| VPC | `10.0.0.0/16`, DNS support + hostnames enabled |
| 2 subnets publicas | `10.0.1.0/24` (us-east-1a), `10.0.2.0/24` (us-east-1b) |
| 2 subnets privadas | `10.0.10.0/24` (us-east-1a), `10.0.11.0/24` (us-east-1b) |
| Internet Gateway | Para trafico saliente desde subnets publicas |
| NAT Gateway + EIP | Para trafico saliente desde subnets privadas |
| Route tables publicas | `0.0.0.0/0` -> IGW |
| Route tables privadas | `0.0.0.0/0` -> NAT |
| SG `clickstream-ecs-tasks-sg` | Ingress: puerto 8080 desde ALB SG. Egress: all traffic |
| SG `clickstream-alb-sg` | Ingress: puerto 80 desde VPC CIDR. Egress: all traffic |

### 2. Toggle ALB para compatibilidad con Floci

Floci no soporta ELBv2 (ALB). Se agrego `enable_alb` (default: `false`) en `infra/environments/local/variables.tf`:

```hcl
variable "enable_alb" {
  type        = bool
  default     = false
  description = "Enable ALB and ECS service (set to true for AWS real, false for Floci)"
}
```

Cuando `enable_alb = false`:
- ALB, target group, listener NO se crean
- ECS service NO se crea
- Lambda NO se asigna a VPC
- `ECS_ENDPOINT` se setea a `http://localhost:8080`

Cuando `enable_alb = true` (AWS real):
- ALB interno, target group, listener se crean en subnets publicas
- ECS service Fargate se despliega en subnets privadas
- Lambda se asigna a VPC (subnets privadas + SG ecs_tasks)
- `ECS_ENDPOINT` se setea a `http://<alb-dns-name>`

### 3. Permisos IAM para Lambda en VPC

Nuevo policy `lambda_vpc_eni` en `infra/modules/iam-roles/main.tf`:

```hcl
Action = [
  "ec2:CreateNetworkInterface",
  "ec2:DescribeNetworkInterfaces",
  "ec2:DeleteNetworkInterface",
  "ec2:AssignPrivateIpAddresses",
  "ec2:UnassignPrivateIpAddresses"
]
Resource = "*"
```

### 4. Lambda vpc_config

`infra/modules/lambda-function/` ahora soporta `vpc_subnet_ids` y `vpc_security_group_ids` (opcionales). Se usa `dynamic "vpc_config"` para solo crear el bloque cuando hay subnets definidas.

### 5. Correccion de outputs duplicados

- `dynamodb-table/main.tf`: outputs movidos a `outputs.tf` (que estaba vacio)
- `api-gateway/main.tf`: outputs duplicados removidos, consolidados en `outputs.tf`
- `s3-bucket/outputs.tf`: creado con `bucket_id`, `bucket_name`, `bucket_arn`

---

## Resultados

### Terraform Plan (enable_alb=false)
```
Plan: 1 to add, 13 to change, 1 to destroy.
```
VPC y sus recursos creados correctamente en Floci.

### Integration tests: 13/13 pasando
```
test_single_heartbeat_returns_response          PASSED
test_single_heartbeat_creates_s3_raw            PASSED
test_single_heartbeat_creates_s3_enriched       PASSED
test_enriched_contains_features_when_enough_hb  PASSED
test_missing_fields_returns_400                 PASSED
test_invalid_json_returns_400                   PASSED
test_dynamodb_session_created                   PASSED
test_different_event_types_all_accepted         PASSED
test_raw_file_content_matches_event             PASSED
test_dynamodb_stores_all_fields_from_event      PASSED
test_dynamodb_event_type_specific_fields        PASSED
test_dynamodb_ttl_is_future_timestamp           PASSED
test_dynamodb_multiple_heartbeats_per_session   PASSED
```

---

## Commit Realizado
```
a831051 feat: add VPC module and production-like network configuration
```

Archivos incluidos:
- `infra/modules/vpc/main.tf` (119 lineas)
- `infra/modules/vpc/variables.tf`
- `infra/modules/vpc/outputs.tf`
- `infra/modules/iam-roles/main.tf` - Lambda VPC ENI policy
- `infra/modules/lambda-function/main.tf` + `variables.tf` - vpc_config
- `infra/modules/ecs-fargate/service/main.tf` - fix `id` instead of `arn`
- `infra/modules/ecs-fargate/task-definition/main.tf` - remove container cpu/memory
- `infra/environments/local/main.tf` - VPC + ALB toggle + condicionales
- `infra/environments/local/variables.tf` - enable_alb variable
- `infra/modules/s3-bucket/outputs.tf` - creado
- `infra/modules/dynamodb-table/main.tf` - outputs removidos
- `infra/modules/api-gateway/main.tf` + `outputs.tf` - duplicados eliminados

---

## Pendiente para Proximas Fases
| Componente | Estado |
|------------|--------|
| ECS Inference server (FastAPI + modelo .pkl) | No iniciado |
| ML Training (scikit-learn/xgboost) | No iniciado |
| Batch Polars (procesamiento analitico) | No iniciado |
| CI/CD | Pendiente |
| Entorno AWS real (enable_alb=true) | Pendiente |