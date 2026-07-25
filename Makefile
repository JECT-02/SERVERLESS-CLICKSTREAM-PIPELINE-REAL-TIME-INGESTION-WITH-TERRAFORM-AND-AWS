.PHONY: help store floci-up floci-down floci-status \
        deploy deploy-aws plan plan-aws destroy destroy-aws tf-init tf-init-aws \
        lambda-package lambda-test lambda-lint \
        ecs-build ecs-test ecs-run-local \
        train train-local \
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
	@echo "=== Clickstream Pipeline - Comandos Disponibles ==="
	@echo ""
	@echo "Entorno Local (Floci):"
	@echo "  make floci-up        - Inicia Floci en puerto 4566"
	@echo "  make floci-down      - Detiene Floci"
	@echo "  make floci-status    - Verifica estado de Floci"
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
	@echo "  make lambda-package  - Empaqueta código Lambda para deploy"
	@echo "  make lambda-test     - Ejecuta tests unitarios Lambda"
	@echo "  make lambda-lint     - Lint código Lambda (ruff/flake8)"
	@echo ""
	@echo "ECS Inference:"
	@echo "  make ecs-build       - Construye imagen Docker ECS"
	@echo "  make ecs-test        - Ejecuta tests ECS inference"
	@echo "  make ecs-run-local   - Ejecuta servidor inference localmente (sin Docker)"
	@echo ""
	@echo "ML Training:"
	@echo "  make train           - Entrena modelo y sube a S3"
	@echo "  make train-local     - Entrena modelo localmente (sin S3)"
	@echo ""
	@echo "Frontend:"
	@echo "  make store           - Abre la tienda en el navegador"
	@echo "  make frontend-install - Instala dependencias npm"
	@echo "  make frontend-test    - Ejecuta tests vitest"
	@echo ""
	@echo "Utilidades:"
	@echo "  make test            - Ejecuta todos los tests (pytest)"
	@echo "  make lint            - Lint todo el proyecto"
	@echo "  make format          - Formatea código (black/ruff)"
	@echo "  make clean           - Limpia artefactos build"
	@echo "  make install         - Instala dependencias Python"

# Floci
floci-up:
	floci start

floci-down:
	floci stop

floci-status:
	curl -s http://localhost:4566/_localstack/health || echo "Floci no responde"

# Terraform Local
tf-init:
	cd $(TERRAFORM_DIR) && terraform init

plan: tf-init
	cd $(TERRAFORM_DIR) && terraform plan

deploy: tf-init
	cd $(TERRAFORM_DIR) && terraform apply -auto-approve

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
	cd $(LAMBDA_DIR) && pip install -r requirements.txt -t package/ && cd package && zip -r ../lambda_package.zip . && cd .. && rm -rf package

lambda-test:
	cd $(LAMBDA_DIR) && python -m pytest tests/ -v

lambda-lint:
	cd $(LAMBDA_DIR) && ruff check src/ tests/ || flake8 src/ tests/

# ECS Inference
ecs-build:
	docker build -t clickstream-inference:latest $(ECS_DIR)

ecs-test:
	cd $(ECS_DIR) && python -m pytest tests/ -v

ecs-run-local:
	cd $(ECS_DIR)/app && python main.py

# ML Training
train:
	cd $(ML_DIR) && python train.py

train-local:
	cd $(ML_DIR) && python train.py --local

# Frontend
store:
	cmd /c start "" "$(FRONTEND_DIR)/index.html"

frontend-install:
	cd $(FRONTEND_DIR) && npm install

frontend-test:
	cd $(FRONTEND_DIR) && npm test

# Utils
test:
	python -m pytest tests/ -v

lint:
	ruff check . || flake8 .

format:
	ruff format . || black .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf lambda/package lambda/lambda_package.zip 2>/dev/null || true

install:
	pip install -r requirements.txt
	cd $(LAMBDA_DIR) && pip install -r requirements.txt
	cd $(ECS_DIR) && pip install -r requirements.txt
	cd $(ML_DIR) && pip install -r requirements.txt
	cd $(BATCH_DIR) && pip install -r requirements.txt