.PHONY: help store floci-up floci-down floci-status check-floci \
        deploy deploy-aws plan plan-aws destroy destroy-aws tf-init tf-init-aws \
        lambda-package lambda-test lambda-lint \
        ecs-build ecs-push ecs-test ecs-run-local \
        train train-local upload-model upload-raw pipeline \
        load-test generate-events \
        frontend-test frontend-install \
        test lint format clean install

# Variables
TERRAFORM_DIR = infra/environments/local
TERRAFORM_AWS_DIR = infra/environments/aws
LAMBDA_DIR = lambda
ECS_DIR = ecs-inference
BATCH_DIR = batch
ML_DIR = ml/training
FRONTEND_DIR = frontend

help:
	@echo "Clickstream Pipeline - Comandos Disponibles"
	@echo ""
	@echo "Entorno Local (Floci):"
	@echo "  make floci-up        - Inicia Floci en puerto 4566"
	@echo "  make floci-down      - Detiene Floci"
	@echo "  make floci-status    - Verifica estado de Floci"
	@echo "  make check-floci     - Verifica que Floci responda (exit 1 si no)"
	@echo ""
	@echo "Infraestructura:"
	@echo "  make deploy          - Despliega infraestructura local (terraform apply)"
	@echo "  make deploy-aws      - Despliega infraestructura en AWS real"
	@echo "  make plan            - Muestra plan terraform local"
	@echo "  make plan-aws        - Muestra plan terraform AWS"
	@echo "  make destroy         - Destruye infraestructura local"
	@echo "  make destroy-aws     - Destruye infraestructura AWS"
	@echo "  make tf-init         - Inicializa Terraform (local)"
	@echo "  make tf-init-aws     - Inicializa Terraform (AWS)"
	@echo ""
	@echo "Lambda:"
	@echo "  make lambda-package  - Empaqueta codigo Lambda para deploy"
	@echo "  make lambda-test     - Ejecuta tests unitarios Lambda"
	@echo "  make lambda-lint     - Lint codigo Lambda (ruff/flake8)"
	@echo ""
	@echo "ECS Inference:"
	@echo "  make ecs-build       - Construye imagen Docker ECS"
	@echo "  make ecs-push        - Taggea y sube imagen a ECR local"
	@echo "  make ecs-test        - Ejecuta tests ECS inference"
	@echo "  make ecs-run-local   - Ejecuta servidor inference localmente (sin Docker)"
	@echo ""
	@echo "ML Training:"
	@echo "  make generate        - Genera datos sinteticos (NDJSON)"
	@echo "  make train           - Entrena modelo y sube a S3"
	@echo "  make train-local     - Entrena modelo localmente (sin S3)"
	@echo "  make upload-model    - Sube modelo local a S3"
	@echo "  make pipeline        - Flujo completo: generate -> polars -> train -> upload"
	@echo ""
	@echo "Testing:"
	@echo "  make load-test       - Ejecuta prueba de carga (scripts/load_test.py)"
	@echo "  make generate-events - Genera eventos de prueba (scripts/generate_events.py)"
	@echo ""
	@echo "Frontend:"
	@echo "  make store           - Abre la tienda en el navegador"
	@echo "  make frontend-install - Instala dependencias npm"
	@echo "  make frontend-test    - Ejecuta tests vitest"
	@echo ""
	@echo "Utilidades:"
	@echo "  make test            - Ejecuta todos los tests (pytest)"
	@echo "  make lint            - Lint todo el proyecto"
	@echo "  make format          - Formatea codigo (black/ruff)"
	@echo "  make clean           - Limpia artefactos build"
	@echo "  make install         - Instala dependencias Python"

# Floci
floci-up:
	floci start

floci-down:
	floci stop

floci-status:
	powershell -NoProfile -File scripts/floci-status.ps1

check-floci:
	powershell -NoProfile -File scripts/check-floci.ps1

# Terraform Local
tf-init:
	cd $(TERRAFORM_DIR) && terraform init

plan: tf-init
	cd $(TERRAFORM_DIR) && terraform plan

deploy: check-floci lambda-package ecs-build tf-init
	cd $(TERRAFORM_DIR) && terraform apply -auto-approve
	powershell -NoProfile -Command "aws ecs update-service --cluster clickstream-cluster --service clickstream-inference-service --force-new-deployment --endpoint-url http://localhost:4566 2>&1 | Out-Null; Start-Sleep -Seconds 2; docker ps --filter 'name=floci-ecs' --format '{{.Names}}' | ForEach-Object { docker stop $$_ 2>&1 | Out-Null }; Write-Host 'ECS reiniciado con nueva imagen'"

destroy:
	cd $(TERRAFORM_DIR) && terraform destroy -auto-approve

# Terraform AWS
tf-init-aws:
	cd $(TERRAFORM_AWS_DIR) && terraform init

plan-aws: tf-init-aws
	cd $(TERRAFORM_AWS_DIR) && terraform plan

deploy-aws: tf-init-aws
	cd $(TERRAFORM_AWS_DIR) && terraform apply -auto-approve

destroy-aws:
	cd $(TERRAFORM_AWS_DIR) && terraform destroy -auto-approve

# Lambda
lambda-package:
	powershell -NoProfile -File scripts/build-lambda.ps1

lambda-test:
	cd $(LAMBDA_DIR) && python -m pytest tests/ -v

lambda-lint:
	cd $(LAMBDA_DIR) && ruff check src/ tests/ || flake8 src/ tests/

# ECS Inference
ecs-build:
	docker build -t clickstream-inference:latest $(ECS_DIR)

ecs-push:
	powershell -NoProfile -Command "docker tag clickstream-inference:latest 000000000000.dkr.ecr.us-east-1.localhost:5100/clickstream-inference:latest; docker push 000000000000.dkr.ecr.us-east-1.localhost:5100/clickstream-inference:latest"

ecs-test:
	cd $(ECS_DIR) && python -m pytest tests/ -v

ecs-run-local:
	cd $(ECS_DIR)/app && python main.py

# Data Generation
DATA_DIR = data

generate:
	cd $(DATA_DIR) && python generate_sessions.py

polars-process:
	python batch/polars_process.py

# ML Training
train: generate polars-process
	cd $(ML_DIR) && python train.py

train-local:
	cd $(ML_DIR) && python train.py --local

upload-raw:
	python scripts/upload_raw.py

upload-model:
	python scripts/upload_model.py

pipeline: clean-data generate polars-process
	cd $(ML_DIR) && python train.py
	python scripts/upload_model.py

load-test:
	python scripts/load_test.py

generate-events:
	python scripts/generate_events.py

# Frontend
store:
	powershell -NoProfile -Command "Start-Process '$(FRONTEND_DIR)/index.html'"

frontend-install:
	cd $(FRONTEND_DIR) && npm install

frontend-test:
	cd $(FRONTEND_DIR) && npm test

# Utils
test: lambda-test ecs-test

lint:
	ruff check . || flake8 .

format:
	ruff format . || black .

clean-data:
	powershell -NoProfile -Command "Remove-Item -Recurse -Force data/raw, data/processed, data/metadata -ErrorAction SilentlyContinue; Write-Host 'Data cleaned'"

clean: clean-data
	powershell -NoProfile -File scripts/clean.ps1

install:
	pip install -r requirements.txt
	cd $(LAMBDA_DIR) && pip install -r requirements.txt
	cd $(ECS_DIR) && pip install -r requirements.txt
	cd $(ML_DIR) && pip install -r requirements.txt
	cd $(BATCH_DIR) && pip install -r requirements.txt