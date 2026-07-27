# Bitacora 5 - Tests Unitarios (41 features) y Tests de Integracion en Floci (9)
**Proyecto:** Serverless Clickstream Pipeline - Real-Time Event Ingestion with Terraform & Polars

## Cambios Realizados

### 1. Tests unitarios de features (41 tests)

**Archivo:** `lambda/tests/test_features.py`

Ampliado de 9 a 41 tests cubriendo todas las funciones nuevas de `features.py`:

| Clase de test | Tests | Funcion probada |
|---------------|-------|-----------------|
| `TestCoreFunctions` | 5 | `calculate_velocity`, `calculate_distance`, `calculate_acceleration`, `detect_exit_intent` |
| `TestDwellSegments` | 3 | `calculate_dwell_segments` |
| `TestClickFrequency` | 3 | `calculate_click_frequency` |
| `TestProductChanges` | 3 | `detect_product_removal`, `detect_product_addition` |
| `TestValueChanges` | 5 | `count_value_changes` |
| `TestAggregateWindow` | 2 | `aggregate_window` |
| `TestExtractCartFeatures` | 3 | `extract_cart_features` |
| `TestExtractFunnelFeatures` | 3 | `extract_funnel_features` |
| `TestExtractAllFeatures` | 2 | `extract_all_features` |

### 2. Tests de integracion contra Floci (9 tests)

**Archivo:** `tests/integration/test_e2e_flow.py`

| Test | Que verifica |
|------|-------------|
| `test_single_heartbeat_returns_response` | Lambda responde JSON con `abandon_probability` y `trigger_retention` |
| `test_single_heartbeat_creates_s3_raw` | Archivo JSON aparece en S3 `raw/` tras POST |
| `test_single_heartbeat_creates_s3_enriched` | Archivo JSON aparece en S3 `enriched/` tras POST |
| `test_enriched_contains_features_when_enough_heartbeats` | Con 6 heartbeats, enriched tiene `velocity_avg`, `heartbeat_count` >= 2 |
| `test_missing_fields_returns_400` | Campos faltantes retornan 400 con `error` |
| `test_invalid_json_returns_400` | JSON invalido retorna 400 con `error` |
| `test_dynamodb_session_created` | DynamoDB tiene item con `event_type`, `ttl` > now |
| `test_different_event_types_all_accepted` | `page_view`, `add_to_cart`, `remove_from_cart`, `start_checkout`, `view_product` aceptados |
| `test_raw_file_content_matches_event` | Contenido del raw en S3 coincide con evento enviado |

### 3. Correcciones en Lambda descubiertas por tests

**Bug 1 - Heartbeat fields ausentes en `session_data['heartbeats']`:**

Lambda construia `heartbeats` solo con `mouse_x`, `mouse_y`, `timestamp`. Las funciones `extract_cart_features()` y `aggregate_window()` filtran por `event_type == 'heartbeat'`, por lo que siempre retornaban valores vacios/default.

**Fix:** `lambda/src/lambda_function.py` ahora incluye `event_type`, `cart_value`, `product_count`, `product_quantities`, `shipping_option_selected`, `mouse_click_count`, `page` en cada heartbeat.

**Bug 2 - DynamoDB sort key colision intra-segundo:**

`store_session_state()` usaba `int(dt.timestamp())` como sort key. Multiples heartbeats en el mismo segundo sobrescribian el item anterior.

**Fix:** `Decimal(str(dt.timestamp()))` preserva milisegundos, eliminando colisiones.

## Resultados

### Unit tests Lambda
```
48 passed (41 features + 7 handler)
```

### Integration tests en Floci
```
9 passed
```

### Flujo E2E verificado
```
POST /events (heartbeat x4)
  -> API Gateway (status 200 x4)
  -> Lambda almacena 4 JSON en S3 raw/
  -> Lambda almacena 4 JSON en S3 enriched/
  -> Lambda escribe 4 items en DynamoDB (sin colision de timestamp)
  -> Lambda calcula features correctamente (hb_count=2,3,4)
  -> Responde {"abandon_probability": 0.0, "trigger_retention": false}
```

## Commit Realizado
```
2170147 test: add feature unit tests (41) and Floci integration tests (9)
```

Archivos incluidos:
- `.gitignore` - ignorar `enriched.json`, `latest_enriched.json`, `_debug_*.py`
- `lambda/src/lambda_function.py` - heartbeat fields completos, timestamp Decimal
- `lambda/tests/test_features.py` - 32 tests nuevos (41 total)
- `lambda/tests/test_lambda_handler.py` - ajustes por heartbeat fields
- `tests/integration/test_e2e_flow.py` - 9 tests contra Floci
- `frontend/config.js` - regenerado por terraform
- `infra/modules/iam-roles/main.tf` - ajuste menor

## Pendiente para Proximas Fases
| Componente | Estado |
|------------|--------|
| ECS Inference server (FastAPI + modelo .pkl) | No iniciado |
| ML Training (scikit-learn/xgboost) | No iniciado |
| Batch Polars (procesamiento analitico) | No iniciado |
| CI/CD | Pendiente |
| Entorno AWS real | Pendiente |