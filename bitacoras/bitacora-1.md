# Bitacora 1 - Estado de Implementacion
**Version:** 1.0  
**Proyecto:** Serverless Clickstream Pipeline - Real-Time Event Ingestion with Terraform & Polars

---

## Componentes Implementados

### 1. Frontend (`frontend/`)
**Archivo principal:** `index.html` (499 lineas)

#### Reglas de Tracking
- Envio de eventos condicionado a: `page` en `["cart", "checkout"]` AND `carrito.length > 0`
- Buffer en catalogo: eventos `view_product`, `add_to_cart`, `page_view` se acumulan y flushean al entrar a cart/checkout con items
- Heartbeat: cada 250ms en cart/checkout con items
- Beforeunload: envia `abandon` via `sendBeacon` si tracking activo

#### Payload Raw Data (sin calculos en frontend)
```json
{
  "event_type": "heartbeat|page_view|add_to_cart|remove_from_cart|view_product|start_checkout|purchase|abandon",
  "timestamp": "ISO8601 UTC",
  "session_id": "uuid-v4",
  "user_id": "uuid-v4 (persistido en localStorage)",
  "mouse_click_count": "integer (acumulativo por sesion)",
  "page": "cart|checkout|catalog",
  "cart_value": "float",
  "product_count": "integer",
  "product_quantities": "{prod_id: qty}",
  "payment_method_selected": "credit_card|debit_card|cash|null",
  "shipping_option_selected": "standard|express|store|null",
  "mouse_x": "integer",
  "mouse_y": "integer",
  "product_id": "string",
  "category": "string",
  "price": "float",
  "abandon_reason": "string"
}
```

#### Configuracion Dinamica
- `config.js` generado por Terraform en `make deploy`
- Fallback hardcodeado para desarrollo sin deploy

### 2. Tests Frontend (`frontend/tests/`) - 22 PASANDO
- **tracking.test.js** (13 tests): validan schema raw por tipo de evento, reglas tracking, buffer/flush
- **api-connection.test.js** (9 tests): validan conexion API Gateway, payloads, headers, error handling

### 3. Infraestructura Terraform (`infra/`)
```
infra/
├── modules/
│   ├── s3-bucket/           # Data lake: raw/, models/, processed/
│   ├── dynamodb-table/      # Sesiones con TTL 60s
│   ├── iam-roles/           # Lambda execution + ECS task execution
│   ├── lambda-function/     # Ingestion handler
│   ├── api-gateway/         # REST API POST /events
│   ├── ecs-fargate/         # Cluster, task-def, service, ALB
│   └── ecr-repo/            # Imagen Docker inference
├── environments/
│   ├── local/               # Floci endpoint localhost:4566
│   └── aws/                 # AWS real (requiere VPC, subnets, SG)
```

#### Recursos Clave
- **S3**: bucket `clickstream-bucket` con versionado + SSE
- **DynamoDB**: tabla `clickstream-sessions` (PK: session_id, SK: timestamp, TTL: 60s)
- **Lambda**: `clickstream-ingestion` (Python 3.11, 512MB, 30s timeout)
- **API Gateway**: REST API `clickstream-api` stage `prod` -> `/events`
- **ECS Fargate**: servicio `clickstream-inference-service` detras de ALB interno
- **ECR**: repo `clickstream-inference` con scan on push

#### Generacion Config Frontend
`null_resource` con `local-exec` genera `frontend/config.js` con `invoke_url` real tras `terraform apply`

### 4. Documentacion
- `docs/api-contract.md`: especificacion completa payload por evento
- `README.md`: guia rapida, comandos Makefile, estructura
- `PLAN_FRONTEND_CONTRACT.md`: plan detallado (en `.opencode/plans/`)

### 5. Automatizacion (`Makefile`)
```bash
make floci-up      # Inicia Floci
make deploy        # Terraform apply local + genera config.js
make store         # Abre tienda en navegador
make frontend-test # 22 tests vitest
make frontend-install
make clean         # Limpia artefactos
```

---

## Flujo de Datos Actual

```
Usuario en catalogo
    -> (view_product, add_to_cart -> BUFFER)
Usuario entra a carrito (items > 0)
    -> FLUSH buffer + page_view
Heartbeat 250ms (mouse_x, mouse_y, cart_value, product_quantities, shipping_option)
    ->
API Gateway -> Lambda -> S3 (raw/) + DynamoDB (session) -> ECS Fargate (/predict)
    ->
Retention modal si trigger_retention
```

---

## Componentes No Implementados

| Componente | Estado |
|------------|--------|
| Lambda `lambda_function.py` | Esqueleto vacio |
| Lambda `features.py` | Vacio |
| ECS Inference `main.py` | Vacio |
| ML Training `train.py` | Vacio |
| Batch Polars `polars_process.py` | Vacio |
| Tests Integracion E2E | Vacio |
| CI/CD GitHub Actions | No |

---

## Comandos de Verificacion

```bash
make floci-up
make deploy
make frontend-test
make store
```

---

## Decisiones Tecnicas

1. **Datos crudos en frontend**: Lambda calcula features derivadas (velocity, idle, distance) para evitar overhead en cliente
2. **Buffer en catalogo**: reduce ruido, solo eventos relevantes llegan a API
3. **250ms heartbeat**: balance latencia/costo; configurable via Terraform
4. **Terraform modular**: mismo codigo para Floci y AWS (cambia provider endpoint)
5. **Config dinámica**: `config.js` generado en deploy -> cero hardcodeo en prod