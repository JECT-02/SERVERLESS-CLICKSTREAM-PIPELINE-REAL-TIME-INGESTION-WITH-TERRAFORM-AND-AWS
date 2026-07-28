# Serverless Clickstream and Predictive ML Pipeline

Real-time event ingestion, purchase propensity inference, and batch analytics pipeline using AWS serverless services, Terraform, and Polars. Runs fully locally via Floci emulator and is portable to real AWS with minimal configuration changes.

## Motivation

E-commerce platforms need to detect cart abandonment in real time to trigger retention actions (free shipping, discounts, express upgrades). This requires a pipeline that ingests clickstream events, runs ML inference with low latency, stores data for batch analytics, and retrains models periodically. The project implements this end-to-end on a serverless architecture to minimize operational overhead and enable auto-scaling.

## What was achieved

- Functional online store frontend that captures mouse position, heartbeats, cart interactions, and delivery mode changes
- Real-time ingestion via API Gateway + Lambda with event validation, S3 persistence, and DynamoDB session windowing
- ML inference on ECS Fargate with a pre-loaded XGBoost model (no cold start) predicting abandonment probability with retention offer selection
- Batch processing pipeline using Polars that reads raw JSON, computes mouse velocity features, idle time, interaction frequency, and exports Parquet datasets
- Automated model retraining with class imbalance handling (SMOTE, class weights) and upload to S3
- Full infrastructure as code with Terraform, deployable locally via Floci or on real AWS

## Technology choices

**Lambda** handles ingestion and orchestration: it receives events via API Gateway, validates and stores them in S3, queries the DynamoDB session window, computes derived features (mouse velocity, idle time), and delegates inference to ECS. Lambda is stateless, auto-scales, and has no infrastructure to manage. It is intentionally kept lightweight and does not load the ML model.

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

## Improvements

- Replace Lambda inference call with async event-driven pattern (SQS + ECS) for higher throughput
- Add API Gateway usage plans, throttling, and API keys for production
- Implement CI/CD pipeline (GitHub Actions) that runs terraform plan on PRs and apply on merge
- Enable S3 versioning and lifecycle policies (transition to Glacier after N days)
- Add CloudWatch dashboards for Lambda duration, ECS CPU/memory, API Gateway latency
- Implement A/B testing for retention offers with different discount values
- Replace local Floci with ephemeral environments per branch using Testcontainers or LocalStack
- Add end-to-end encryption for production data in transit and at rest
