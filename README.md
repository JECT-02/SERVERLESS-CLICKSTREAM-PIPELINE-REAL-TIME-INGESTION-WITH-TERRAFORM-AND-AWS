# Serverless Clickstream Pipeline

Pipeline MLOps completo para captura de clickstream en tiempo real, inferencia de abandono de carrito y procesamiento batch con Polars.

## Arquitectura

```
Frontend (HTML/JS) -> API Gateway -> Lambda -> S3 (raw) + DynamoDB (session)
                                          |
                                          -> ECS Fargate (ML inference)
Batch: S3 (raw) -> Polars -> S3 (processed/Parquet) -> Retraining -> S3 (models)
```

## Requisitos

- Python 3.11+
- Terraform >= 1.5
- Floci (emulador AWS local) o cuenta AWS real
- Docker (para ECS inference)
- Node.js 20+ (para tests frontend)

## Inicio Rapido (Local con Floci)

```bash
# 1. Instalar dependencias
make install

# 2. Iniciar Floci
make floci-up

# 3. Desplegar infraestructura
make deploy

# 4. Abrir frontend
make store
```

## Comandos Principales

```bash
# Infraestructura
make deploy          # Deploy local (Floci)
make deploy-aws      # Deploy AWS real
make destroy         # Destruir local
make plan            # Ver plan terraform

# Lambda
make lambda-package  # Empaquetar lambda
make lambda-test     # Tests unitarios lambda

# ECS Inference
make ecs-build       # Build imagen Docker
make ecs-test        # Tests ECS
make ecs-run-local   # Ejecutar inference local

# ML
make train           # Entrenar modelo y subir a S3
make train-local     # Entrenar local

# Tests y Calidad
make test            # Todos los tests
make lint            # Lint proyecto
make format          # Formatear codigo
make clean           # Limpiar artefactos

# Frontend
make store           # Abrir tienda
```

## Estructura

```
├── frontend/           # Tienda simulada HTML/JS
│   ├── index.html      # Frontend principal
│   ├── config.js       # Config generada por Terraform
│   ├── assets/         # JS/CSS
│   └── tests/          # Tests vitest
├── lambda/             # Funcion ingestion
│   ├── src/            # Codigo Python
│   └── tests/          # Tests unitarios
├── ecs-inference/      # Servicio ML en ECS Fargate
│   ├── app/            # FastAPI /predict
│   └── tests/          # Tests
├── ml/training/        # Entrenamiento modelo
├── batch/              # Procesamiento Polars
├── infra/              # Terraform
│   ├── modules/        # Modulos reutilizables
│   └── environments/   # local/ | aws/
├── scripts/            # Utilidades
└── tests/integration/  # Tests E2E
```

## Configuracion Frontend

`frontend/config.js` se genera automaticamente en `make deploy`:

```javascript
window.CLICKSTREAM_CONFIG = {
  apiUrl: "https://xxx.execute-api.us-east-1.amazonaws.com/prod/events",
  trackedPages: ["cart", "checkout"],
  heartbeatIntervalMs: 3000
};
```

Reglas de tracking:
- Solo envia eventos en paginas `cart` o `checkout`
- Solo si carrito tiene >= 1 item
- Heartbeat cada 3s en esas condiciones

## Tests Frontend

```bash
cd frontend
npm install
npm test
```

## Variables de Entorno

Copiar `.env.example` a `.env` y ajustar:

```bash
cp .env.example .env
```

## Migracion a AWS Real

1. Configurar credenciales AWS en `.env` o `aws configure`
2. Ajustar `infra/environments/aws/terraform.tfvars`:
   - `vpc_id`, `subnet_ids`, `alb_security_group_ids`
   - `ecs_image` (URI de ECR)
3. Ejecutar `make deploy-aws`

## Licencia

MIT