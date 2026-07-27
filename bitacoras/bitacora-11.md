# Bitacora 11 - Pipeline Automatizado S3 a Modelo
**Proyecto:** Serverless Clickstream Pipeline - Real-Time Event Ingestion with Terraform & Polars

---

## Cambios Realizados

### Scripts nuevos

| Archivo | Proposito |
|---------|-----------|
| `scripts/upload_raw.py` | Sube `data/raw/all_events.ndjson` a `s3://clickstream-bucket/raw/` |

### Scripts modificados

| Archivo | Cambio |
|---------|--------|
| `batch/polars_process.py` | Crea `data/processed/` si no existe |

### Makefile

| Target | Comando |
|--------|---------|
| `make upload-raw` | Sube raw data local a S3 |
| `make pipeline` | Flujo completo: upload-raw -> download -> polars -> train -> upload-model |

### Flujo automatizado

```
make pipeline
  -> upload_raw.py      sube NDJSON local a S3
  -> download_from_s3.py descarga desde S3
  -> polars_process.py   bronze/silver/gold
  -> train.py            XGBoost
  -> upload_model.py     sube .pkl a S3
```

### Verificacion

```
$ aws s3 ls s3://clickstream-bucket/raw/
2026-07-26   82860101 all_events.ndjson

$ aws s3 ls s3://clickstream-bucket/models/
2026-07-26     292663 modelo_propension.pkl
```

## Commit

```
6d7b134 feat: pipeline automatizado completo S3 -> local -> modelo -> S3
```
