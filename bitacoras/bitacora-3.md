# Bitacora 3 - Integracion API Gateway con Lambda
**Version:** 1.0
**Proyecto:** Serverless Clickstream Pipeline - Real-Time Event Ingestion with Terraform & Polars

---

## Implementacion: Conexion API Gateway a Lambda

### Arquitectura de Integracion

API Gateway recibe peticiones HTTP POST en el endpoint `/events` y las reenvia a la funcion Lambda mediante integracion `AWS_PROXY`. Lambda procesa el evento, persiste en S3 y DynamoDB, calcula features, e invoca inferencia en ECS Fargate.

### Recursos Terraform

**Modulo API Gateway** (`infra/modules/api-gateway/main.tf`):

| Recurso | Descripcion |
|---------|-------------|
| `aws_api_gateway_rest_api.api` | REST API `clickstream-api` |
| `aws_api_gateway_resource.events` | Recurso `/events` bajo el path raiz |
| `aws_api_gateway_method.post` | Metodo HTTP `POST` en `/events` con `authorization = "NONE"` |
| `aws_api_gateway_integration.lambda` | Integracion `AWS_PROXY` que conecta POST /events con Lambda |
| `aws_api_gateway_deployment.deployment` | Despliegue de la API |
| `aws_api_gateway_stage.stage` | Stage `prod` que sirve la API |

**Modulo Lambda** (`infra/modules/lambda-function/main.tf`):

| Recurso | Descripcion |
|---------|-------------|
| `aws_lambda_function.ingestion` | Funcion `clickstream-ingestion` (Python 3.11, 512MB, 30s timeout) |
| `aws_lambda_permission.api_gateway_invoke` | Permiso para que API Gateway invoque Lambda |

**Conexion entre modulos:**

```
API Gateway (api-gateway module)
  uri = lambda_function.invoke_arn               -> puede invocar Lambda
  execution_arn es pasado a lambda-function module -> source_arn del permiso

Lambda Function (lambda-function module)
  lambda_permission.source_arn = api_gateway.execution_arn  -> permite invocacion
  invoke_arn es usado por api-gateway como uri de integracion
```

### Flujo de Datos: API Gateway a Lambda

```
POST /events (JSON payload)
  |
  v
API Gateway (AWS_PROXY integration)
  |
  | Evento completo de API Gateway:
  | {
  |   "resource": "/events",
  |   "path": "/events",
  |   "httpMethod": "POST",
  |   "headers": {...},
  |   "queryStringParameters": null,
  |   "pathParameters": null,
  |   "requestContext": {...},
  |   "body": "{\"event_type\":\"heartbeat\",...}",
  |   "isBase64Encoded": false
  | }
  |
  v
Lambda (lambda_function.lambda_handler)
  |
  | 1. Extrae event['body'] (string JSON)
  | 2. Parsea a dict
  | 3. Valida contra EVENT_TYPE_SCHEMAS
  | 4. Genera s3_key = raw/YYYY/MM/DD/{type}_{session}_{uuid}.json
  | 5. s3.put_object -> S3 bucket (path-style: /clickstream-bucket/raw/...)
  | 6. dynamodb.put_item -> Tabla clickstream-sessions (TTL 60s)
  | 7. dynamodb.query -> Historial de sesion (heartbeats recientes)
  | 8. calculate_mouse_features() -> velocity, idle, distance, trend
  | 9. POST /predict -> ECS Fargate (inferencia)
  | 10. Retorna respuesta al frontend
  |
  v
Respuesta JSON (200 OK)
{
  "abandon_probability": 0.82,
  "trigger_retention": true,
  "retention_type": "coupon",
  "coupon_code": "SAVE10"
}
```

### Lambda Handler: Logica Interna

**Validacion** (`validate_event`):
- Cada tipo de evento tiene un esquema definido en `EVENT_TYPE_SCHEMAS`
- Campos requeridos base: `event_type`, `session_id`, `user_id`, `timestamp`
- Heartbeat requiere ademas: `cart_value`, `product_count`, `product_quantities`, `shipping_option_selected`, `mouse_click_count`, `mouse_x`, `mouse_y`, `page`
- Retorna 400 si faltan campos o event_type es invalido

**Almacenamiento en S3** (`store_event_s3`):
- Ruta: `raw/{YYYY}/{MM}/{DD}/{event_type}_{session_id}_{uuid8}.json`
- Contenido: JSON completo del evento (serializado con `default=str`)
- Particionado por fecha para facilitar procesamiento batch futuro con Polars

**Estado de Sesion en DynamoDB** (`store_session_state`):
- Partition Key: `session_id` (String)
- Sort Key: `timestamp` (Number, epoch seconds)
- Atributos: `user_id`, `event_type`, `cart_value` (Decimal), `product_count`, `product_quantities` (Map), `shipping_option_selected`, `mouse_click_count`, `mouse_x`, `mouse_y`, `page`, `s3_key`
- TTL: 60 segundos (limpieza automatica)
- `to_dynamo_value()` convierte `float` a `Decimal` (requerido por DynamoDB)

**Historial de Sesion** (`get_session_history`):
- Query por `session_id`, orden ascendente por timestamp
- Retorna items recientes para calcular ventana de heartbeats

**Features del Mouse** (`calculate_mouse_features` en `features.py`):
- Requiere al menos 2 heartbeats en la sesion
- Calcula por par consecutivo:
  - Distancia euclidiana: `sqrt((x2-x1)^2 + (y2-y1)^2)`
  - Velocidad: distancia / delta tiempo (px/ms)
  - Tiempo idle: segmentos con velocidad < 0.01 px/ms
  - Tendencia de velocidad: decreasing / stable / increasing
- Retorna: `velocity_avg`, `idle_total_ms`, `distance_total`, `velocity_trend`

**Inferencia** (`invoke_inference`):
- Envia POST al endpoint `{ECS_ENDPOINT}/predict` con payload de features
- Timeout: 5 segundos
- Si ECS no responde o no esta disponible, retorna fallback `{abandon_probability: 0.0, trigger_retention: false}`

### IAM Roles y Permisos

**Rol Lambda** (`clickstream-ingestion-execution-role`):

| Politica | Acciones | Recursos |
|----------|----------|----------|
| `lambda_s3_write` | `s3:PutObject`, `s3:GetObject` | `${bucket}/raw/*`, `${bucket}/models/*` |
| `lambda_dynamodb` | `dynamodb:PutItem`, `dynamodb:Query`, `dynamodb:GetItem` | Tabla `clickstream-sessions` |
| `lambda_logs` | `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents` | `*` |

**Permiso API Gateway** (`aws_lambda_permission`):
- Principal: `apigateway.amazonaws.com`
- Accion: `lambda:InvokeFunction`
- Source ARN: `arn:aws:execute-api:{region}:{account}:{api-id}/*/POST/events`

### Variables de Entorno Lambda

| Variable | Valor | Proposito |
|----------|-------|-----------|
| `S3_BUCKET` | `clickstream-bucket` | Bucket para eventos raw y modelos |
| `DYNAMODB_TABLE` | `clickstream-sessions` | Tabla de estado de sesion |
| `AWS_ENDPOINT_URL` | *(inyectado por Floci)* | Endpoint de Floci para servicios AWS locales |
| `ECS_ENDPOINT` | `http://localhost:8080` | Endpoint del servicio de inferencia ECS |

### Pruebas Unitarias (Lambda)

7 tests en `lambda/tests/test_lambda_handler.py`:
- `test_lambda_handler_valid_event` - evento valido retorna 200
- `test_lambda_handler_missing_fields` - campos faltantes retornan 400
- `test_lambda_handler_invalid_json` - JSON invalido retorna 400
- `test_lambda_handler_different_event_types` - todos los tipos de evento son aceptados
- `test_lambda_handler_s3_key_format` - formato de clave S3 correcto
- `test_lambda_handler_dynamodb_item_structure` - estructura de item DynamoDB correcta
- `test_lambda_handler_response_structure` - estructura de respuesta JSON correcta

### Archivos Relacionados

- `lambda/src/lambda_function.py` - handler principal (validacion, S3, DynamoDB, features, inference)
- `lambda/src/features.py` - calculo de features del mouse (velocity, idle, distance, trend)
- `infra/modules/api-gateway/main.tf` - configuracion API Gateway REST
- `infra/modules/api-gateway/outputs.tf` - outputs: rest_api_id, stage_name, invoke_url, execution_arn
- `infra/modules/lambda-function/main.tf` - configuracion Lambda + permiso API Gateway
- `infra/modules/iam-roles/main.tf` - roles IAM y politicas
- `lambda/tests/test_lambda_handler.py` - tests unitarios del handler
