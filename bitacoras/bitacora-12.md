# Bitacora 12 - Servidor de Inferencia ECS con Modelo desde S3
**Proyecto:** Serverless Clickstream Pipeline - Real-Time Event Ingestion with Terraform & Polars

## Cambios Realizados

### Archivos nuevos

| Archivo | Proposito |
|---------|-----------|
| `ecs-inference/app/model_loader.py` | Descarga modelo .pkl desde S3 al arrancar y lo mantiene en memoria |
| `ecs-inference/app/schema.py` | Modelos Pydantic para request/response |
| `ecs-inference/app/inference.py` | Mapeo de features Lambda -> modelo XGBoost, prediccion y seleccion de retencion |
| `ecs-inference/app/main.py` | FastAPI con endpoints /health y /predict, carga el modelo en startup |
| `ecs-inference/Dockerfile` | python:3.11-slim, expone puerto 8080 |
| `ecs-inference/tests/test_inference.py` | 9 tests de preprocesamiento, mapeo, retencion y estructura de respuesta |

### Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `ecs-inference/requirements.txt` | Agregado xgboost, pandas, numpy, httpx |
| `infra/environments/local/variables.tf` | ecs_env_vars default con S3_BUCKET + MODEL_S3_KEY |
| `infra/environments/aws/main.tf` | Merge de S3_BUCKET + MODEL_S3_KEY en ECS task definition |

### Arquitectura de Cold Start

```
Contenedor ECS arranca
  -> lifespan de FastAPI
  -> model_loader.load_model()
  -> boto3 descarga s3://clickstream-bucket/models/modelo_propension.pkl
  -> joblib.load() extrae: modelo XGBoost, scaler, encoder, feature_cols
  -> Modelo queda en memoria global (singleton)
  -> /predict recibe features desde Lambda, mapea a 29 columnas, predice
```

### Mapeo de features

Lambda envia ~20 features en tiempo real (velocity, idle, dwell, cart, etc). El servidor ECS las mapea a las 29 del modelo entrenado (27 numericas + device categorica), rellena con 0 las faltantes, aplica StandardScaler + LabelEncoder y ejecuta XGBoost.

### Endpoints

| Endpoint | Metodo | Descripcion |
|----------|--------|-------------|
| `/health` | GET | Estado del servicio y modelo cargado |
| `/predict` | POST | Recibe features, devuelve abandon_probability + retention |

### Tests

```
9 passed in 2.77s
```

## Commit

```
(no commit yet)
```
