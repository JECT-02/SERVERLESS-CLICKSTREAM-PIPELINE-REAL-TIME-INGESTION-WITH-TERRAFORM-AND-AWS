# Serverless Clickstream and Predictive ML Pipeline

Real-time event ingestion, purchase propensity inference, and batch analytics pipeline using AWS serverless services, Terraform, and Polars. Runs fully locally via Floci emulator and is portable to real AWS with minimal configuration changes.

## Motivation

Globally, 70.22% of online shopping carts are abandoned before purchase (Baymard Institute, meta-analysis of 49 studies, 2025). That is 7 out of every 10 visitors who add a product leave without buying, representing an estimated $260 billion in recoverable order value annually in the US and EU alone (Baymard, 2025). The top fixable cause, cited by 39% of US abandoners, is unexpected extra costs at checkout (Baymard, 2024).

E-commerce platforms need to detect cart abandonment in real time and trigger retention actions such as free shipping, discounts, or express upgrades before the user leaves. This requires a pipeline that ingests clickstream events, runs ML inference with low latency, stores data for batch analytics, and retrains models periodically. The project implements this end-to-end on a serverless architecture to minimize operational overhead and enable auto-scaling.

## What was achieved

- Functional online store frontend capturing mouse position, heartbeats, cart interactions, and delivery mode changes
- Real-time ingestion via API Gateway + Lambda with event validation, S3 persistence, and DynamoDB session windowing
- ML inference on ECS Fargate with a pre-loaded XGBoost model (no cold start) predicting abandonment probability with retention offer selection
- Batch processing pipeline using Polars that reads raw JSON, computes mouse velocity features, idle time, interaction frequency, and exports Parquet datasets
- Automated model retraining with class imbalance handling (SMOTE, class weights) and upload to S3
- Full infrastructure as code with Terraform, deployable locally via Floci or on real AWS

## Why each technology

**Lambda** handles ingestion and orchestration: receives events via API Gateway, validates and stores them in S3, queries the DynamoDB session window, computes derived features (mouse velocity, idle time), and delegates inference to ECS. Lambda is stateless, auto-scales, and requires no infrastructure management. It is intentionally kept lightweight and does not load the ML model.

**ECS Fargate** runs the ML model as a FastAPI service with the model pre-loaded in memory at container startup. Unlike Lambda (max 15 min execution, 10 GB memory, cold start), Fargate supports models of any size, has no cold start for inference, and allows larger CPU/memory allocations. The inference service receives feature vectors and returns probability with retention type.

**Floci** emulates AWS services (S3, Lambda, API Gateway, DynamoDB, ECS, ECR, IAM) locally on port 4566. It enables full development and testing without an AWS account, credentials, or costs. The same Terraform configuration works against Floci locally and AWS production by changing the provider endpoint.

**Polars** processes raw JSON events into structured Parquet datasets with lazy evaluation and high throughput. It computes derived mouse features (euclidean distance between consecutive positions, velocity, idle segments) and session-level aggregations for model training.

**Terraform** defines all cloud resources declaratively: S3 bucket, DynamoDB table, ECS cluster/task/service, ALB, Lambda function, API Gateway, IAM roles, and ECR repository. Resources are modular and reusable across environments.

## Architecture

```
Frontend (HTML/JS, localhost:8000)
  -> POST /api/events (proxy)
    -> API Gateway (Floci localhost:4566)
      -> Lambda (ingestion, validation, features)
        -> S3 (raw JSON partitioned by date)
        -> DynamoDB (session state, TTL 60s)
        -> ECS Fargate (XGBoost inference via ALB)

Batch (triggered manually or scheduled):
  S3 raw JSON -> Polars (clean, feature engineering) -> Parquet -> Train model -> Upload .pkl to S3
```

## Project structure

```
infra/               Terraform modules and environments (local, aws)
lambda/              Lambda ingestion function
ecs-inference/       FastAPI inference service container
ml/training/         Model training script
batch/               Polars processing pipeline
frontend/            Online store (HTML/JS + Python proxy)
scripts/             Build, deploy, destroy, push utilities
data/                Raw NDJSON, processed Parquet, models
```

---

# Serverless Clickstream and Predictive ML Pipeline (espanol)

Pipeline de ingesta de eventos en tiempo real, inferencia de propension de compra y procesamiento batch analitico usando servicios serverless de AWS, Terraform y Polars. Se ejecuta completamente en local mediante el emulador Floci y es portable a AWS real con cambios minimos de configuracion.

## Motivacion

Globalmente, el 70.22% de los carritos de compra online son abandonados antes de completar la compra (Baymard Institute, meta-analisis de 49 estudios, 2025). Es decir, 7 de cada 10 visitantes que agregan un producto se van sin comprar, lo que representa un estimado de $260 mil millones en pedidos recuperables anualmente solo en EE.UU. y la UE (Baymard, 2025). La causa principal evitable, citada por el 39% de los abandonadores en EE.UU., son los costos extra inesperados al finalizar la compra (Baymard, 2024).

Las tiendas online necesitan detectar abandono de carrito en tiempo real y activar acciones de retencion (envio gratis, descuentos, upgrade express) antes de que el usuario se vaya. Esto requiere un pipeline que ingiera eventos de clickstream, ejecute inferencia ML con baja latencia, almacene datos para analitica batch y reentrene modelos periodicamente. El proyecto implementa esto de extremo a extremo sobre una arquitectura serverless para minimizar costos operativos y permitir auto-escalado.

## Que se logro

- Tienda online funcional que captura posicion del mouse, heartbeats, interacciones con carrito y cambios de tipo de envio
- Ingesta en tiempo real via API Gateway + Lambda con validacion de eventos, persistencia en S3 y ventana de sesion en DynamoDB
- Inferencia ML en ECS Fargate con modelo XGBoost precargado en memoria (sin cold start) que predice probabilidad de abandono y selecciona oferta de retencion
- Pipeline batch con Polars que lee JSON crudos, calcula features de velocidad del mouse, tiempo idle, frecuencia de interaccion y exporta datasets Parquet
- Reentrenamiento automatizado del modelo con manejo de desbalanceo de clases (SMOTE, class weights) y subida a S3
- Infraestructura completa como codigo con Terraform, desplegable localmente via Floci o en AWS real

## Por que cada tecnologia

**Lambda** maneja la ingesta y orquestacion: recibe eventos via API Gateway, los valida y almacena en S3, consulta la ventana de sesion en DynamoDB, calcula features derivadas (velocidad del mouse, tiempo idle) y delega la inferencia a ECS. Lambda es stateless, auto-escalable y no requiere gestion de infraestructura. Se mantiene intencionalmente liviana y no carga el modelo ML.

**ECS Fargate** ejecuta el modelo ML como un servicio FastAPI con el modelo precargado en memoria al iniciar el contenedor. A diferencia de Lambda (max 15 min de ejecucion, 10 GB de memoria, cold start), Fargate soporta modelos de cualquier tamano, no tiene cold start para inferencia y permite asignar mas CPU/memoria. El servicio recibe vectores de features y devuelve probabilidad con tipo de retencion.

**Floci** emula servicios AWS (S3, Lambda, API Gateway, DynamoDB, ECS, ECR, IAM) en local en el puerto 4566. Permite desarrollar y probar completamente sin cuenta AWS, credenciales ni costos. La misma configuracion Terraform funciona contra Floci en local y contra AWS en produccion solo cambiando el endpoint del provider.

**Polars** procesa eventos JSON a datasets Parquet estructurados con evaluacion lazy y alto rendimiento. Calcula features derivadas de mouse (distancia euclidiana entre posiciones consecutivas, velocidad, segmentos idle) y agregaciones a nivel de sesion para entrenamiento del modelo.

**Terraform** define todos los recursos cloud de forma declarativa: bucket S3, tabla DynamoDB, cluster/tarea/servicio ECS, ALB, funcion Lambda, API Gateway, roles IAM y repositorio ECR. Los recursos son modulares y reutilizables entre entornos.

## Arquitectura

```
Frontend (HTML/JS, localhost:8000)
  -> POST /api/events (proxy)
    -> API Gateway (Floci localhost:4566)
      -> Lambda (ingesta, validacion, features)
        -> S3 (JSON crudos particionados por fecha)
        -> DynamoDB (estado de sesion, TTL 60s)
        -> ECS Fargate (inferencia XGBoost via ALB)

Batch (ejecucion manual o programada):
  S3 JSON crudos -> Polars (limpieza, ingenieria features) -> Parquet -> Entrenar modelo -> Subir .pkl a S3
```

## Estructura del proyecto

```
infra/               Modulos y entornos Terraform (local, aws)
lambda/              Funcion Lambda de ingesta
ecs-inference/       Contenedor FastAPI para inferencia
ml/training/         Script de entrenamiento del modelo
batch/               Pipeline de procesamiento con Polars
frontend/            Tienda online (HTML/JS + proxy Python)
scripts/             Utilidades de build, deploy, destroy, push
data/                NDJSON crudo, Parquet procesado, modelos
```

## Improvements / Mejoras posibles

- Replace synchronous Lambda-to-ECS call with async event-driven pattern (SQS + ECS) for higher throughput
- Add API Gateway usage plans, throttling, and API keys for production
- Implement CI/CD pipeline (GitHub Actions) with terraform plan on PRs and apply on merge
- Enable S3 versioning and lifecycle policies (transition to Glacier after N days)
- Add CloudWatch dashboards for Lambda duration, ECS CPU/memory, API Gateway latency
- Implement A/B testing for retention offers with different discount values
- Replace local Floci with ephemeral environments per branch using Testcontainers or LocalStack
- Add end-to-end encryption for production data in transit and at rest
