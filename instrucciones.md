# Instrucciones Rapidas

```powershell
make floci-up                # Inicia Floci
make install                 # Instala dependencias Python
make deploy                  # Despliega toda la infraestructura
make store                   # Abre la tienda en el navegador
```

Mientras usas la tienda, genera interacciones (ver productos, carrito, checkout). Los heartbeats se envían cada 3s y el modelo ML infiere probabilidad de abandono. Al superar 0.7 aparecen ofertas de retención.

Para detener todo:

```powershell
make destroy                 # Destruye infraestructura local
make floci-down              # Detiene Floci
```

Otros comandos utiles:

```powershell
make test                    # Ejecuta tests (Lambda + ECS)
make generate                # Genera datos sinteticos (NDJSON)
make train                   # generate + polars + entrena modelo + sube a S3
make pipeline                # clean-data + generate + polars + train + upload
make clean-data              # Elimina data/raw, data/processed, data/metadata
```
