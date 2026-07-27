# Bitacora 9 - Pipeline de Procesamiento y Entrenamiento de Modelo
**Proyecto:** Serverless Clickstream Pipeline - Real-Time Event Ingestion with Terraform & Polars


## Cambios Realizados

### Scripts creados

| Archivo | Proposito |
|---------|-----------|
| `scripts/download_from_s3.py` | Descarga NDJSON desde S3 (individual o consolidado). Fallback a local si S3 no disponible. 189,406 eventos descargados |
| `batch/polars_process.py` | Pipeline medallion: bronze (cast, particion por fecha), silver (velocity, idle, dwell, exit-intent), gold (agregacion por sesion + target abandon/purchase) |
| `ml/training/data_prep.py` | Carga gold.parquet, LabelEncoder para device, StandardScaler para 28 features numericas, split estratificado 80/20 |
| `ml/training/train.py` | XGBoost con scale_pos_weight para desbalanceo (70/30). Guarda modelo + scaler + encoders + feature names en .pkl |
| `ml/training/evaluate.py` | Precision, recall, F1, specificity, AUC-ROC, AUC-PR. Escribe training_report.json |

### Pipeline ejecutado

| Capa | Filas | Descripcion |
|------|-------|-------------|
| Bronze | 189,406 | Eventos crudos desde NDJSON con tipos normalizados |
| Silver | 169,251 | Heartbeats con velocity, acceleration, idle_ms, dwell_ms, exit-intent flags |
| Gold | 5,000 | Sesiones agregadas con 28 features + target abandoned |

### Metricas del modelo (XGBoost)

| Metrica | Valor |
|---------|-------|
| Precision | 0.9986 |
| Recall | 1.0000 |
| F1 Score | 0.9993 |
| AUC-ROC | 0.99997 |
| AUC-PR | 0.99999 |
| Specificity | 0.9966 |

### Correcciones durante ejecucion

1. **Schema inference de NDJSON**: columnas `payment_method`, `abandon_reason` no existian en el primer batch de lectura. Fix: `infer_schema_length=None` para escanear todo el archivo
2. **Deprecacion Polars**: `how='outer'` reemplazado por `how='full'`
3. **Filter type mismatch**: columnas Int64 no pueden ser predicate de filter, convertidas a condicion `== 1`

### Limpieza del repositorio

- `data/processed/` y `data/metadata/` agregados a `.gitignore`
- Arquivos regenerables eliminados (bronze.parquet, silver.parquet, gold.parquet, sessions.parquet, generation_report.json)
- `frontend/config.js`, `tests/integration/` removidos de tracking
- Directorios basura fisicos eliminados: `lambda/package/`, `test_extract/`, `lambda_package.zip`, `__pycache__/`
