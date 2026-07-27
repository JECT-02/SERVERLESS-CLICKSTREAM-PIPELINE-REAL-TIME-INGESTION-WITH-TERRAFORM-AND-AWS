# Bitacora 10 - Subida de Modelo a S3
**Proyecto:** Serverless Clickstream Pipeline - Real-Time Event Ingestion with Terraform & Polars

---

## Cambios Realizados

### Script: `scripts/upload_model.py`

Sube `data/models/modelo_propension.pkl` a `s3://clickstream-bucket/models/` y exporta `MODEL_S3_PATH`.

| Variable | Valor |
|----------|-------|
| Bucket | `clickstream-bucket` |
| Key | `models/modelo_propension.pkl` |
| PATH | `s3://clickstream-bucket/models/modelo_propension.pkl` |

### `.env.example`

Agregado `MODEL_S3_KEY=models/modelo_propension.pkl`.

### `Makefile`

Agregado target `upload-model`:
```bash
make upload-model  # python scripts/upload_model.py
```

### Verificacion

```
$ aws s3 ls s3://clickstream-bucket/models/
2026-07-26 19:54:41     292663 modelo_propension.pkl
```

## Commit

```
278dccb feat: script upload_model.py + variable MODEL_S3_PATH
```
