# Bitacora 13 - Ventana de 3 Minutos en Lambda e Inferencia ECS Completa
**Proyecto:** Serverless Clickstream Pipeline - Real-Time Event Ingestion with Terraform & Polars

## Cambios Realizados

### Lambda: ventana temporal en DynamoDB

`get_session_history()` ahora filtra por `session_id AND timestamp >= ahora - 180s`:

```python
SESSION_WINDOW_SECONDS = 180
KeyConditionExpression='session_id = :sid AND #ts >= :cutoff'
ScanIndexForward=False  # mas recientes primero
```

### ECS: modelo descargado de S3 al arrancar

`model_loader.py` descarga `s3://clickstream-bucket/models/modelo_propension.pkl` en el lifespan de FastAPI y lo mantiene en memoria como singleton.

### Flujo completo de inferencia

```
Frontend -> POST /events
  -> API Gateway
  -> Lambda handler
     -> valida evento
     -> guarda raw JSON en S3 raw/YYYY/MM/DD/
     -> guarda item en DynamoDB (session_id PK, timestamp SK, TTL 3600s)
     -> consulta DynamoDB: ultimos 180s de heartbeats
     -> extract_all_features(): velocity, acceleration, idle, dwell, exit-intent, etc
     -> prepare_inference_payload(): arma payload con ~20 features
     -> invoke_inference(): POST /predict a ECS
        -> ECS recibe features
        -> mapea a 29 columnas del modelo
        -> aplica StandardScaler + LabelEncoder
        -> XGBoost predice probabilidad de abandono
        -> select_retention_type(): shipping_discount / express_upgrade / coupon
        -> retorna {abandon_probability, trigger_retention, retention_type}
     -> store_enriched_event_s3(): guarda raw + features + inference
     -> retorna respuesta al frontend
```

### Pruebas

```
ecs-inference/tests/test_inference.py: 9/9 passed
```

### Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `lambda/src/lambda_function.py` | `get_session_history()` con filtro de 180s, orden descendente |
