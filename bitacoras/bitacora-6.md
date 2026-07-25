# Bitacora 6 - Conexion y Almacenamiento en DynamoDB como Cache de Sesion
**Fecha:** 2026-07-25
**Proyecto:** Serverless Clickstream Pipeline - Real-Time Event Ingestion with Terraform & Polars

---

## Cambios Realizados

### 1. Conexion dedicada a DynamoDB

**Archivo:** `lambda/src/lambda_function.py`

`connect_dynamodb()` creada como funcion independiente que encapsula la creacion del recurso boto3, permitiendo reuso y mejor testabilidad:

```python
def connect_dynamodb() -> object:
    resource = boto3.resource('dynamodb', endpoint_url=AWS_ENDPOINT_URL, config=Config(
        region_name=AWS_REGION,
        retries={'max_attempts': 3, 'mode': 'standard'}
    ))
    return resource.Table(DYNAMODB_TABLE)
```

### 2. Almacenamiento dinamico de todos los campos del evento

`store_session_state()` refactorizada para:
- Almacenar cualquier campo presente en `event_data` que este en la lista `DYNAMODB_FIELDS`
- TTL aumentado de 60s a 3600s (1 hora) para servir como cache de sesion del modelo
- `SESSION_CACHE_TTL_SECONDS = 3600` como constante de modulo

**Nuevos campos almacenados:**

| Campo | Tipo | Eventos donde aparece |
|-------|------|----------------------|
| `device` | String | heartbeat, page_view, etc. |
| `delivery_mode` | String | heartbeat |
| `shipping_type` | String | heartbeat |
| `shipping_cost` | Decimal | heartbeat |
| `payment_method` | String | purchase |
| `abandon_reason` | String | abandon |
| `product_id` | String | add_to_cart, view_product |
| `category` | String | add_to_cart, view_product |
| `price` | Decimal | add_to_cart, view_product |

`DYNAMODB_FIELDS` lista completa:
```python
['device', 'delivery_mode', 'shipping_type', 'shipping_cost',
 'abandon_reason', 'payment_method', 'product_id', 'category', 'price',
 'cart_value', 'product_count', 'product_quantities',
 'shipping_option_selected', 'mouse_click_count', 'mouse_x', 'mouse_y',
 'page', 'user_id', 'event_type']
```

### 3. Outputs de Terraform

**Archivo:** `infra/modules/dynamodb-table/outputs.tf`

Completado con 4 outputs: `table_name`, `table_arn`, `table_hash_key`, `table_range_key`.

---

## Tests

### Unit tests Lambda: 53/53 pasando (12 handler + 41 features)

Nuevos tests en `test_lambda_handler.py`:

| Test | Que verifica |
|------|-------------|
| `test_dynamodb_item_ttl_expiry_value` | TTL >= now + 3590s |
| `test_dynamodb_stores_device_field` | device, delivery_mode, shipping_type, shipping_cost guardados |
| `test_dynamodb_stores_event_type_specific_fields` | payment_method (purchase), abandon_reason (abandon), product_id/category/price (add_to_cart) |
| `test_dynamodb_does_not_store_absent_optional_fields` | Campos no enviados no aparecen en el item |
| `test_dynamodb_put_item_called_for_each_event` | Cada evento invoca put_item |

### Integration tests Floci: 13/13 pasando

Nuevos tests en `test_e2e_flow.py`:

| Test | Que verifica |
|------|-------------|
| `test_dynamodb_stores_all_fields_from_event` | device, delivery_mode, shipping_type, shipping_cost persisten en DynamoDB |
| `test_dynamodb_event_type_specific_fields` | payment_method para purchase, abandon_reason para abandon |
| `test_dynamodb_ttl_is_future_timestamp` | ttl > now + 3000s |
| `test_dynamodb_multiple_heartbeats_per_session` | 3 heartbeats = 3 items, timestamps en orden ascendente |

---

## Commit Realizado
```
2f2839b feat: add dedicated DynamoDB connection, expand session storage to all event fields
```

Archivos incluidos:
- `lambda/src/lambda_function.py` - connect_dynamodb(), DYNAMODB_FIELDS, TTL 3600s
- `lambda/tests/test_lambda_handler.py` - 5 nuevos tests DynamoDB
- `tests/integration/test_e2e_flow.py` - 4 nuevos tests integracion DynamoDB
- `infra/modules/dynamodb-table/outputs.tf` - outputs completos
- `bitacoras/bitacora-5.md` - bitacora anterior

---

## Pendiente para Proximas Fases
| Componente | Estado |
|------------|--------|
| ECS Inference server (FastAPI + modelo .pkl) | No iniciado |
| ML Training (scikit-learn/xgboost) | No iniciado |
| Batch Polars (procesamiento analitico) | No iniciado |
| CI/CD | Pendiente |
| Entorno AWS real | Pendiente |