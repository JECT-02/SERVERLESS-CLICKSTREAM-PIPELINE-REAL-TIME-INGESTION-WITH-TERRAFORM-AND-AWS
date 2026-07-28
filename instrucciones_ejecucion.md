# Instrucciones de Ejecucion

## Clonar e iniciar

```powershell
git clone https://github.com/JECT-02/SERVERLESS-CLICKSTREAM-PIPELINE-REAL-TIME-INGESTION-WITH-TERRAFORM-AND-AWS
cd SERVERLESS-CLICKSTREAM-PIPELINE-REAL-TIME-INGESTION-WITH-TERRAFORM-AND-AWS
make floci-up
make install
make deploy
make store
```

La tienda se abre en `http://localhost:8000`. Navega por productos, agrega al carrito, ve al checkout. El modelo ML infiere abandono y muestra ofertas de retencion si supera 0.7 de probabilidad.

Para detener: `make destroy` + `make floci-down`.

## Comandos

| Comando | Que hace |
|---------|----------|
| `make floci-up` | Inicia Floci (emulador AWS local) |
| `make install` | Instala dependencias Python |
| `make deploy` | Terraform + push ECS + upload datos + entrena modelo |
| `make store` | Abre tienda online + proxy API |
| `make test` | Ejecuta tests unitarios |
| `make train` | Procesa datos y entrena modelo |
| `make pipeline` | clean-data + generate + polars + train |
| `make destroy` | Destruye infraestructura local |

## Requerimientos

- Python 3.11+
- Docker Desktop
- Floci CLI (`winget install floci`)
- Terraform (`winget install terraform`)
- AWS CLI (`winget install awscli`)
- Git LFS (`git lfs install`)
