.PHONY: help store floci-up floci-down deploy destroy

help:
	@echo Comandos disponibles:
	@echo   make store     - Abre la tienda en el navegador
	@echo   make floci-up  - Inicia Floci
	@echo   make floci-down - Detiene Floci
	@echo   make deploy    - Ejecuta terraform apply
	@echo   make destroy   - Ejecuta terraform destroy

store:
	start index.html

floci-up:
	floci start

floci-down:
	floci stop

deploy:
	terraform apply -auto-approve

destroy:
	terraform destroy -auto-approve
