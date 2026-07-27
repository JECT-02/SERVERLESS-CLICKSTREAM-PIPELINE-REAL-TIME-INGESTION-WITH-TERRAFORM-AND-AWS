# Bitacora 4 - Correccion de Fallos y Verificacion en Floci
**Version:** 2.0
**Proyecto:** Serverless Clickstream Pipeline - Real-Time Event Ingestion with Terraform & Polars

---

## Fallos Detectados y Corregidos

### 1. S3 Bucket DNS en Floci (virtual-hosted style)
**Problema:** Terraform creaba bucket S3 con virtual-hosted style (`bucket.localhost:4566`), que no resuelve DNS en Floci.
**Solucion:** `s3_use_path_style = true` en provider AWS + `s3={'addressing_style': 'path'}` en boto3 Config del Lambda.

### 2. ALB / Target Group (ELBv2)
**Problema:** Floci no soporta ELBv2, retorna `InvalidClientTokenId` 403.
**Solucion:** Removidos modulos `alb` y `ecs-service` del entorno local. ECS Cluster, Task Definition y ECR repo se mantienen (Floci los soporta parcialmente). La inferencia ECS se integrara cuando el servidor FastAPI/Flask este listo.

### 3. `null_resource` heredoc en Windows
**Problema:** `local-exec` con heredoc (`<<-EOT`) no funciona en PowerShell.
**Solucion:** Reemplazado por `local_file` resource del provider `hashicorp/local`.

### 4. DynamoDB Float Types
**Problema:** DynamoDB rechaza `float` de Python, requiere `Decimal`.
**Solucion:** Funcion `to_dynamo_value()` con `Decimal(str(value))` para todo valor numerico en `store_session_state()`.

### 5. Lambda no accede a Floci services
**Problema:** `AWS_ENDPOINT_URL=http://localhost:4566` explicitamente seteado en Lambda sobreescribe la inyeccion automatica de Floci (`http://floci:4566`), lo que impide que Lambda containerizado alcance el host Floci.
**Solucion:** Eliminado `AWS_ENDPOINT_URL` de las variables de entorno de Lambda. Floci lo inyecta automaticamente. Fallback local a `http://localhost:4566`.

### 6. Timestamp Decimal de DynamoDB
**Problema:** DynamoDB retorna `Number` como `Decimal`. `parse_timestamp()` en features.py no lo manejaba, causando error `'decimal.Decimal' object cannot be interpreted as an integer`.
**Solucion:** `parse_timestamp()` ahora convierte `Decimal`/`int`/`float` a `datetime` via `datetime.fromtimestamp(float(ts))`.

### 7. `__pycache__` en Lambda zip
**Problema:** Zip incluia `__pycache__/` que aumentaba tamaño y podia causar errores de importacion.
**Solucion:** Zip creado excluyendo `__pycache__` con `Compress-Archive -Path *.py`.

---

## Verificacion en Floci

### Recursos Creados por Terraform
| Recurso | Estado |
|---------|--------|
| S3 bucket `clickstream-bucket` | Creado, versionado, SSE habilitado |
| DynamoDB `clickstream-sessions` | Creado, TTL 60s |
| IAM Lambda execution role | Creado con permisos S3, DynamoDB, logs |
| IAM ECS task execution role | Creado con permisos S3, logs |
| Lambda `clickstream-ingestion` | Desplegado, handler `lambda_function.lambda_handler` |
| API Gateway `clickstream-api` | REST API, POST /events, stage prod |
| ECS cluster `clickstream-cluster` | Creado |
| ECS task definition `clickstream-inference` | Creado |
| ECR repo `clickstream-inference` | Creado |
| Frontend config `frontend/config.js` | Generado con URL Floci correcta |

### Pruebas End-to-End
```
POST /events (heartbeat)
  -> API Gateway (status 200)
  -> Lambda almacena JSON en S3 raw/2026/07/25/heartbeat_*.json
  -> Lambda escribe sesion en DynamoDB (ttl, cart_value, product_quantities, mouse_x/y)
  -> Lambda consulta historial de sesion (heartbeat recientes)
  -> Lambda calcula features (velocity, idle, distance)
  -> Lambda intenta inferencia ECS (fallback 0.0 porque ECS no corre)
  -> Responde {"abandon_probability": 0.0, "trigger_retention": false}
```

### Estado Tests Unitarios
- Lambda: 7/7 pasando
- Frontend: 22/22 pasando (de sesion previa)

---

## Commit Realizado
```
97b344d fix: resolve Floci S3 path-style, DynamoDB Decimal, Lambda networking, and Windows heredoc
```

Archivos incluidos:
- `.gitignore` - ignore temp test artifacts + lambda zip
- `infra/environments/local/main.tf` - S3 path-style, ALB removido, local_file, auto hash
- `infra/environments/local/variables.tf` - AWS_ENDPOINT_URL removido de Lambda env
- `lambda/src/lambda_function.py` - Decimal support, timestamp fix, mejor error handling
- `lambda/src/features.py` - parse_timestamp maneja Decimal/epoch seconds

---

## Pendiente para Proximas Fases

| Componente | Estado |
|------------|--------|
| ECS Inference server (FastAPI + modelo .pkl) | No iniciado |
| ML Training (scikit-learn/xgboost) | No iniciado |
| Batch Polars (procesamiento analitico) | No iniciado |
| Tests integracion E2E automatizados | Pendiente |
| CI/CD | Pendiente |
| Entorno AWS real | Pendiente |
