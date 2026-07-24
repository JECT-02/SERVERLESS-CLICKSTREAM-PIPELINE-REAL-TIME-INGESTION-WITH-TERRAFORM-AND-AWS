GUIA DEL PROYECTO: SERVERLESS CLICKSTREAM AND PREDICTIVE ML PIPELINE

1. IDENTIFICACION DEL PROYECTO

Nombre: Serverless Clickstream and Predictive ML Pipeline: Real-Time Ingestion and Purchase Propensity with Terraform and Polars.

Proposito: Construir un pipeline completo de MLOps que simule una tienda online, capture eventos de clic en tiempo real, almacene datos crudos en un data lake local, ejecute inferencia de propension de abandono de carrito mediante un modelo de machine learning, y procese lotes de datos historicos con un motor analitico de alto rendimiento.

Entorno de ejecucion: Floci, un emulador local de servicios cloud que permite ejecutar AWS, Azure y GCP en la laptop sin credenciales ni costos. Para este proyecto se utilizara el emulador de AWS de Floci en el puerto 4566, el cual soporta mas de sesenta servicios incluyendo S3, Lambda, API Gateway, IAM y DynamoDB, y es compatible con Terraform, AWS CLI y los SDKs oficiales de AWS.

Tecnologias principales e implicancias:
- Frontend: HTML y JavaScript.
  Implicancia: simula una tienda online real sin necesidad de frameworks complejos. Genera eventos JSON que se envian al endpoint local.
- Backend serverless: AWS API Gateway, AWS Lambda (Python) y ECS Fargate.
  Servicios de Floci usados: API Gateway, Lambda, ECS.
  Implicancia: API Gateway recibe eventos HTTP y los pasa a Lambda. Lambda maneja la ingestion y el estado de sesion en DynamoDB, y delega la inferencia del modelo a ECS Fargate via HTTP interno. ECS mantiene el modelo cargado en memoria sin cold start, permitiendo mayor memoria, CPU y modelos pesados.
- Almacenamiento: Amazon S3.
  Servicio de Floci usado: S3.
  Implicancia: data lake centralizado para JSON crudos, modelos .pkl y archivos Parquet. En Floci el almacenamiento es local y volatil si no se persiste. En AWS real requiere versionado, politicas de ciclo de vida y control de acceso.
- Machine learning: Scikit-Learn y XGBoost.
  Implicancia: el modelo se ejecuta en ECS Fargate, no hay limite de 250 MB. El modelo se carga en memoria al iniciar el contenedor y responde peticiones sin cold start. Requiere manejo de desbalanceo de clases y metricas adecuadas para datos sesgados.
- Procesamiento analitico: Polars.
  Implicancia: lee JSONs acumulados en S3, realiza limpieza, ingenieria de caracteristicas y exporta Parquet de forma rapida. Se ejecuta como script batch programado en la laptop.
- Infraestructura como codigo: Terraform.
  Implicancia: define todos los recursos AWS de forma reproducible. En Floci apunta a localhost:4566. Para AWS real solo se cambia el provider y las credenciales.
- Entorno local: Floci como emulador AWS.
  Servicios de Floci usados: S3, Lambda, API Gateway, IAM, DynamoDB, ECS.
  Implicancia: permite desarrollar y probar sin cuenta ni costos de AWS. No es produccion. ECS se emula como contenedores locales gestionados por Floci o como proceso Python directo.

2. OBJETIVOS GENERALES

Objetivo 1: Disenar y desplegar una arquitectura serverless completamente local que reciba eventos HTTP, los procese en Lambda y los almacene en S3.

Objetivo 2: Entrenar un modelo de clasificacion binaria que prediga la probabilidad de abandono de carrito con rigor matematico, incluyendo manejo de desbalanceo de clases.

Objetivo 3: Ejecutar inferencia en tiempo real dentro de la funcion Lambda, respondiendo al frontend en milisegundos para activar acciones de retencion.

Objetivo 4: Procesar periodicamente los datos acumulados en S3 mediante Polars, generando reportes limpios y optimizados en formato Parquet.

Objetivo 5: Automatizar todo el despliegue de infraestructura con Terraform, garantizando reproducibilidad y portabilidad hacia AWS real.

3. FASES DEL PROYECTO

FASE 1: PREPARACION DEL ENTORNO LOCAL

Objetivo: Tener un entorno de desarrollo funcional con Python, Floci, Terraform, AWS CLI y las librerias necesarias.

Pasos:
1. Instalar Python 3.11 o superior y crear un entorno virtual.
2. Instalar las librerias de Python: boto3, polars, scikit-learn, xgboost, pandas, numpy, joblib, pyarrow.
3. Instalar Floci CLI y ejecutar Floci en el puerto 4566.
4. Configurar las variables de entorno para apuntar a Floci:
   - AWS_ENDPOINT_URL=http://localhost:4566
   - AWS_ACCESS_KEY_ID=test
   - AWS_SECRET_ACCESS_KEY=test
   - AWS_REGION=us-east-1
5. Instalar Terraform y verificar que funcione con el provider de AWS apuntando al endpoint local.
6. Instalar AWS CLI y verificar con aws s3 ls --endpoint-url http://localhost:4566.

Implicancias: Floci emula AWS localmente. No se requiere cuenta ni credenciales reales, pero el comportamiento final debe validarse en AWS real antes de produccion.

Criterio de aceptacion: El comando aws s3 ls retorna una lista vacia sin errores y Terraform init se ejecuta correctamente.

FASE 2: DISENO DE LA ARQUITECTURA

Objetivo: Definir como fluyen los datos desde el frontend hasta el almacenamiento analitico, incluyendo los componentes de inferencia y procesamiento batch.

Componentes:
- Frontend HTML/JavaScript: simula una tienda online. Captura posicion del mouse (x, y) en crudo envia heartbeats cada 3s via fetch POST a API Gateway. Recibe respuestas de inferencia y muestra ofertas de retencion.

- API Gateway: endpoint REST unico POST /events. Recibe los JSON del frontend y los reenvia a Lambda.

- Lambda (ingestion y estado): recibe el evento, lo valida, guarda en S3, escribe y consulta DynamoDB para la ventana de heartbeat. Calcula features basicas y envia peticion HTTP interna a ECS Fargate para la inferencia del modelo. Recibe la respuesta y la retorna al frontend.

- ECS Fargate (inferencia): servicio contenerizado que ejecuta un servidor FastAPI/Flask con el modelo .pkl pre-cargado en memoria al arrancar. Expone un endpoint POST /predict que recibe features y devuelve probabilidad de abandono + retention_type. No tiene cold start, soporta hasta 30GB de memoria y modelos pesados (XGBoost, Random Forest grandes, redes neuronales). Escala horizontalmente segun demanda.

- DynamoDB: session state store temporal. Guarda solo los ultimos segundos de cada sesion activa con TTL de 60s. Lambda consulta las ultimas N filas para construir la ventana de tiempo y calcular features.

- S3: data lake de tres capas:
  - raw/: JSONs individuales escritos por Lambda.
  - models/: archivo .pkl del modelo entrenado.
  - processed/: datasets Parquet generados por Polars.

- Script batch Polars (local): lee JSONs desde S3, limpia, calcula features de mouse y heartbeat, agrupa por sesion, exporta Parquet a S3. Luego entrena modelo nuevo con esos datos y sube .pkl a S3.

Flujo completo de datos:

Frontend --POST /events--> API Gateway
                               |
                               v
                            Lambda
                               |
                    +----------+-----------+
                    |          |           |
                    v          v           v
                 DynamoDB    ECS        Respuesta
                (ventana   Fargate      (inferencia
                 de 15s)   /predict      sincrona)
                    |          |
                    |          +--- modelo .pkl
                    |               (en memoria,
                    |               sin cold start)
                    v
                   S3
               (data lake)
                    |
            +-------+-------+
            |               |
            v               v
        raw/ (JSONs)   models/ (.pkl)
            |
            v
       Polars (local)
            |
            v
      processed/ (Parquet)
            |
            v
      Entrenamiento -> .pkl -> S3 models/

Estructura de carpetas en S3:
- s3://clickstream-bucket/raw/year=YYYY/month=MM/day=DD/evento_id.json
- s3://clickstream-bucket/models/modelo_propension.pkl
- s3://clickstream-bucket/processed/entrenamiento.parquet

Criterio de aceptacion: Existe un diagrama de arquitectura validado y una lista de recursos Terraform identificados.

FASE 3: CREACION DEL FRONTEND DE SIMULACION

Objetivo: Construir una interfaz web simple que genere eventos de usuario y muestre alertas de retencion basadas en la inferencia.

Pasos:
1. Crear un archivo index.html con una tienda ficticia de productos con catalogo, carrito en dos columnas, checkout, modal de retencion y selector de tipo de entrega (recojo en tienda / envio a domicilio).
2. Capturar eventos de interaccion: visualizacion de producto, agregar/quitar del carrito, cambio de tipo de envio, inicio de checkout, abandono de pagina.
3. Capturar posicion del mouse (mouse_x, mouse_y) en tiempo real mediante event listener de mousemove. Incluir estas coordenadas en crudo en cada evento sin calcular velocidad ni idle en el frontend.
4. Implementar heartbeat periodico cada 3 segundos. Enviar evento de tipo heartbeat con la pagina actual, mouse_x, mouse_y, timestamp y estado del carrito. No enviar si la pestana esta oculta.
5. Enviar cada evento como JSON mediante fetch POST al endpoint de API Gateway local.
6. Recibir la respuesta de la Lambda. Si trigger_retention es true, mostrar modal dinamico segun retention_type: shipping_discount (envio gratis), express_upgrade (express sin recargo) o cupon de descuento.
7. Al hacer clic en "abandonar carrito", mostrar modal con motivos predefinidos. Enviar evento abandon con abandon_reason al seleccionar.

Ejemplo de payload JSON (evento de interaccion):
{
  "user_id": "uuid",
  "session_id": "uuid",
  "event_type": "add_to_cart",
  "product_id": "prod_001",
  "category": "computacion",
  "price": 1200,
  "timestamp": "2026-07-05T10:30:00Z",
  "device": "desktop",
  "cart_value": 1200,
  "cart_items": 1,
  "time_on_page": 45,
  "mouse_x": 320,
  "mouse_y": 180
}

Ejemplo de payload JSON (heartbeat):
{
  "user_id": "uuid",
  "session_id": "uuid",
  "event_type": "heartbeat",
  "page": "cart",
  "timestamp": "2026-07-05T10:31:00Z",
  "time_on_page": 60,
  "mouse_x": 320,
  "mouse_y": 180,
  "cart_value": 1285,
  "cart_items": 2,
  "delivery_mode": "shipping",
  "shipping_cost": 8,
  "shipping_type": "standard"
}

Criterio de aceptacion: El frontend envia eventos correctamente y recibe respuestas JSON del endpoint local.

FASE 4: INFRAESTRUCTURA COMO CODIGO CON TERRAFORM

Objetivo: Definir y desplegar todos los recursos AWS de forma reproducible mediante archivos de configuracion Terraform.

Recursos a crear:
1. Bucket S3 para clickstream, modelos y archivos Parquet.
2. Tabla DynamoDB con session_id como partition key y timestamp como sort key, con TTL habilitado.
3. ECS Cluster (Fargate) para alojar el servicio de inferencia.
4. ECR repositorio para la imagen Docker del modelo.
5. ECS Task Definition con definicion de contenedor: imagen desde ECR, puerto 8080, variables de entorno (endpoint S3, nombre del modelo), asignacion de memoria y CPU.
6. ECS Service (Fargate) que corre la tarea con target group para balanceo.
7. Application Load Balancer (internal) para balancear peticiones entre las tareas ECS.
8. Rol IAM de ejecucion para ECS con permisos de lectura sobre S3 (para descargar .pkl).
9. Rol IAM de ejecucion para Lambda con permisos minimos sobre S3, DynamoDB, ECS (invoke) y logs.
10. Funcion Lambda de Python para ingestion.
11. API Gateway REST con metodo POST y recurso /events.
12. Permisos necesarios para que API Gateway invoque Lambda.

Buenas practicas:
- Usar nombres de recursos descriptivos.
- Aplicar el principio de menor privilegio en politicas IAM.
- Definir variables en variables.tf para facilitar cambios entre entornos.
- Usar outputs.tf para exponer el endpoint de API Gateway.

Comandos principales:
- terraform init
- terraform plan
- terraform apply
- terraform destroy

Implicancias: Los recursos se crean en Floci, no en AWS real. El mismo codigo Terraform sirve para produccion cambiando el endpoint del provider AWS y las credenciales.

Criterio de aceptacion: terraform apply crea todos los recursos sin errores y el endpoint /events responde localmente.

FASE 5: DESARROLLO DE LA FUNCION LAMBDA DE INGESTION E INFERENCIA

Objetivo: Implementar la logica serverless que reciba eventos, los persista en S3 y ejecute inferencia de machine learning en tiempo real.

Pasos:
1. Crear el handler lambda_function.py con firma lambda_handler(event, context).
2. Parsear el body del evento proveniente de API Gateway.
3. Validar campos obligatorios y normalizar el timestamp.
4. Construir el registro JSON completo con todos los campos del evento.
5. Almacenar el evento crudo en S3 con la ruta particionada por fecha.
6. Escribir una fila en DynamoDB con session_id como PK y timestamp como SK, incluyendo campos relevantes (mouse_x, mouse_y, cart_value, delivery_mode, etc.). TTL de 60s para limpieza automatica.
7. Consultar DynamoDB: query por session_id, limit a 5 filas, orden descendente. Obtener la ventana de heartbeats recientes.
8. Si hay menos de 3 filas en la ventana, saltar inferencia y devolver respuesta neutra. Si hay suficientes, calcular metricas derivadas:
   - Distancia euclidiana entre posiciones mouse consecutivas.
   - Delta tiempo entre heartbeats.
   - Velocidad del mouse por segmento y promedio de la ventana.
   - Tiempo idle acumulado (segmentos con velocidad < umbral).
   - Tendencia de velocidad (si esta bajando progresivamente).
9. Construir payload de features: mouse_velocity_avg, idle_seconds, session_duration, page_changes, cart_interactions, shipping_toggles, delivery_mode, cart_value.
10. Enviar peticion HTTP POST al endpoint interno del ALB de ECS Fargate (/predict) con el payload de features. El contenedor ECS tiene el modelo cargado en memoria y responde en milisegundos.
11. Si probabilidad > umbral (ej: 0.7), seleccionar retention_type segun contexto:
    - Envio gratis (shipping_discount) si delivery_mode es shipping y shipping_cost > 0.
    - Upgrade express (express_upgrade) si shipping_type es standard.
    - Cupon de descuento (coupon) en caso contrario.
12. Responder al frontend con JSON sincrono: probabilidad, trigger_retention, retention_type, coupon_code.

Ejemplo de respuesta (cupon):
{
  "abandon_probability": 0.82,
  "trigger_retention": true,
  "retention_type": "coupon",
  "coupon_code": "SAVE10"
}

Ejemplo de respuesta (envio gratis):
{
  "abandon_probability": 0.85,
  "trigger_retention": true,
  "retention_type": "shipping_discount",
  "coupon_code": null
}

Ejemplo de respuesta (express upgrade):
{
  "abandon_probability": 0.78,
  "trigger_retention": true,
  "retention_type": "express_upgrade",
  "coupon_code": null
}

Ejemplo de respuesta (sin retencion):
{
  "abandon_probability": 0.12,
  "trigger_retention": false
}

Consideraciones tecnicas:
- Lambda se encarga solo de ingestion y estado, no carga el modelo. La inferencia se delega a ECS.
- El contenedor ECS descarga el .pkl desde S3 al iniciarse (una sola vez) y lo mantiene en memoria.
- ECS Fargate soporta hasta 30GB de memoria y 16 vCPU, sin limite de tiempo de ejecucion.
- En Floci, ECS se emula como un contenedor local. Para desarrollo local sin ECS, se puede ejecutar el servidor de inferencia directamente con Python.

Implicancias: Separar ingestion (Lambda) de inferencia (ECS) elimina el cold start del modelo, permite modelos de cualquier tamano y escala independiente. Lambda responde rapido porque solo orquesta.

Criterio de aceptacion: Lambda recibe un evento, lo guarda en S3, consulta DynamoDB, llama a ECS para inferencia y responde al frontend en menos de 500 ms en entorno local.

FASE 6: ENTRENAMIENTO DEL MODELO DE PROPENSION DE COMPRA

Objetivo: Entrenar un modelo de clasificacion binaria robusto que prediga si un usuario abandonara el carrito.

Pasos:
1. Generar o obtener un dataset historico de sesiones de usuario con eventos de clickstream.
2. Definir la variable objetivo: 1 si la sesion abandono el carrito, 0 si completo la compra.
3. Realizar ingenieria de caracteristicas:
   - Numero de productos vistos.
   - Tiempo total en sesion.
   - Valor del carrito.
   - Numero de eventos por tipo.
   - Ratio de productos agregados versus vistos.
   - Categoria predominante.
   - Dispositivo y fuente de trafico.
   - Velocidad promedio del mouse durante la sesion (calculada a partir de heartbeats: distancia entre mouse_x, mouse_y consecutivos / delta timestamp).
   - Tiempo idle total (periodos donde el mouse no se movio entre heartbeats).
   - Frecuencia de interaccion (eventos por minuto).
   - Tiempo en pagina carrito antes de accion.
   - Cambios de tipo de envio (standard a express, envio a recogida).
4. Dividir el dataset en entrenamiento y prueba con estratificacion.
5. Manejar el desbalanceo de clases mediante:
   - Class_weight balanced.
   - SMOTE u oversampling.
   - Ajuste de umbrales de decision.
6. Entrenar modelos candidatos: Logistic Regression, Random Forest, Gradient Boosting, XGBoost.
7. Evaluar con metricas adecuadas para desbalanceo: precision, recall, F1-score, AUC-ROC, AUC-PR.
8. Seleccionar el mejor modelo y exportarlo como archivo .pkl con joblib.
9. Subir el modelo al bucket S3 en s3://clickstream-bucket/models/.

Criterio de aceptacion: El modelo seleccionado tiene un AUC-PR superior a 0.6 y un tamano de archivo inferior a 100 MB.

FASE 7: PROCESAMIENTO BATCH CON POLARS

Objetivo: Extraer, limpiar, transformar y compactar los eventos acumulados en S3 utilizando Polars para generar datasets analiticos eficientes.

Origen de datos: los archivos JSON en s3://clickstream-bucket/raw/ son escritos directamente por Lambda en cada invocacion.

Pasos:
1. Listar todos los archivos JSON almacenados en s3://clickstream-bucket/raw/ de las sesiones a procesar.
2. Descargar los archivos y cargarlos en un DataFrame de Polars de forma lazy cuando sea posible. Usar scan_json para lectura optimizada.
3. Limpiar datos:
   - Eliminar duplicados por event_id o combinacion session_id + timestamp.
   - Corregir tipos de datos (timestamps a datetime, numericos a float).
   - Tratar valores nulos en campos opcionales.
   - Filtrar eventos fuera de rango temporal o de prueba.
4. Ordenar eventos por timestamp dentro de cada session_id.
5. Calcular features derivadas a partir de datos crudos de mouse:
   - Calcular distancia euclidiana entre posiciones mouse consecutivas: sqrt((x2-x1)^2 + (y2-y1)^2).
   - Calcular delta tiempo entre eventos consecutivos (en segundos).
   - Derivar velocidad del mouse: distancia / delta tiempo (px/s).
   - Identificar periodos idle: segmentos con velocidad < 5 px/s.
   - Calcular tiempo idle total por sesion.
   - Calcular frecuencia de interaccion: conteo de eventos no-heartbeat por minuto.
6. Crear caracteristicas agregadas por sesion (una fila por sesion):
   - Total de eventos.
   - Duracion total de la sesion.
   - Valor maximo del carrito alcanzado.
   - Cantidad de categorias distintas vistas.
   - Secuencia de tipos de evento (pagina de entrada, pagina de salida).
   - Velocidad promedio del mouse.
   - Tiempo idle total y porcentaje idle sobre duracion total.
   - Cantidad de cambios de tipo de envio/entrega.
   - Tiempo desde ultimo evento hasta abandono o compra.
   - Flag de compra (1 si la sesion tiene evento purchase, 0 si tiene abandon).
7. Unir las sesiones que tienen flag de compra o abandono como variable objetivo.
8. Guardar el dataset procesado en formato Parquet particionado por fecha en s3://clickstream-bucket/processed/.
9. El script de entrenamiento lee el Parquet desde S3, entrena el modelo localmente con los features generados, evalua metricas y exporta el .pkl a s3://clickstream-bucket/models/.
10. Programar la ejecucion del script mediante cron, schedule o un orquestador local.

Criterio de aceptacion: El script de Polars procesa al menos diez mil eventos en menos de treinta segundos y genera archivos Parquet validos.

FASE 8: ORQUESTACION Y AUTOMATIZACION

Objetivo: Integrar todos los componentes en un flujo automatizado y documentado.

Pasos:
1. Crear un Makefile o script de automatizacion con las siguientes tareas:
   - start: levantar Floci.
   - stop: detener Floci.
   - deploy: ejecutar Terraform apply.
   - train: entrenar y subir el modelo.
   - ingest: enviar eventos de prueba.
   - process: ejecutar el script batch de Polars.
   - test: ejecutar pruebas unitarias e integracion.
   - destroy: eliminar la infraestructura local.
2. Versionar el codigo en un repositorio Git con estructura clara.
3. Incluir un archivo requirements.txt o pyproject.toml con dependencias exactas.
4. Documentar las variables de entorno necesarias.

Criterio de aceptacion: Es posible levantar todo el pipeline con un solo comando y reproducir el flujo completo en una laptop nueva.

FASE 9: PRUEBAS Y VALIDACION

Objetivo: Verificar que cada componente funcione correctamente de forma aislada e integrada.

Pruebas unitarias:
- Validacion de payloads JSON.
- Transformacion de features para el modelo.
- Funciones de lectura y escritura en S3.
- Calculo de metricas del modelo.

Pruebas de integracion:
- Envio de eventos desde el frontend al endpoint.
- Verificacion de que los eventos llegan a S3 correctamente.
- Verificacion de que DynamoDB almacena y expira filas correctamente.
- Verificacion de que Lambda llama a ECS Fargate y recibe respuesta de inferencia.
- Verificacion de que la respuesta de inferencia llega al frontend.
- Ejecucion completa del script batch y validacion del Parquet generado.

Pruebas de carga:
- Enviar cien o mas eventos por segundo durante un minuto.
- Medir latencia p50, p95 y p99 de la Lambda local.

Implicancias: Las pruebas de carga en Floci validan logica y latencia local, pero no reflejan completamente concurrencia, throttling ni latencia de red de AWS real. Antes de produccion se deben ejecutar pruebas adicionales en una cuenta AWS.

Criterio de aceptacion: El sistema procesa eventos sin perdida de datos, la latencia p95 es menor a un segundo, y el script batch finaliza sin errores.

FASE 10: DOCUMENTACION Y ENTREGA

Objetivo: Entregar un proyecto profesional, bien documentado y listo para portar a AWS real.

Entregables:
1. Codigo fuente completo en repositorio Git.
2. Archivos Terraform para despliegue local y guia de adaptacion a AWS real.
3. Notebook o script de entrenamiento del modelo.
4. Script de procesamiento batch con Polars.
5. Frontend HTML/JavaScript funcional.
6. Documentacion de arquitectura.
7. Manual de despliegue y pruebas.
8. Resultados de metricas del modelo y pruebas de carga.

Recomendaciones para migrar a AWS real:
- Cambiar el endpoint de Terraform al provider oficial de AWS.
- Revisar los limites de concurrencia de Lambda y ajustar el timeout segun la latencia de ECS.
- Configurar Auto Scaling para ECS Fargate basado en CPU/memoria o en peticiones por target.
- Habilitar ECR para la imagen Docker del modelo y automatizar el build con CI/CD.
- Configurar bucket S3 con versionado y politicas de ciclo de vida para transicionar datos viejos a S3 Glacier.
- Habilitar CloudWatch para logs y metricas de Lambda, ECS y API Gateway.
- Considerar API Gateway con throttling, autorizacion y usage plans.

4. REFERENCIAS Y FUENTES DE INVESTIGACION

- Floci: emulador local de servicios cloud. Compatible con AWS, Azure y GCP. Permite ejecutar AWS CLI, SDKs y Terraform sobre localhost sin credenciales. Sitio oficial: https://floci.io
- Terraform: herramienta de infraestructura como codigo de HashiCorp para definir, provisionar y versionar recursos cloud. Documentacion oficial: https://developer.hashicorp.com/terraform/docs
- AWS Lambda: servicio de computacion serverless para ingestion y orquestacion ligera. Documentacion oficial: https://docs.aws.amazon.com/lambda/latest/dg/welcome.html
- Amazon ECS Fargate: servicio de contenedores serverless que ejecuta el modelo de ML sin gestionar servidores. Carga el .pkl en memoria al arrancar y responde inferencias sin cold start. Documentacion oficial: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/what-is-fargate.html
- Polars: libreria DataFrame de alto rendimiento escrita en Rust, con soporte para Lazy API, streaming, Parquet, JSON y consultas sobre grandes volumenes de datos. Documentacion oficial: https://docs.pola.rs
- Scikit-Learn y XGBoost: librerias de machine learning para clasificacion binaria, con soporte para manejo de desbalanceo y exportacion de modelos con joblib.

5. NOTAS FINALES

Este proyecto demuestra un perfil de MLOps de extremo a extremo. La combinacion de Floci, Terraform, Lambda, S3, Polars y Scikit-Learn permite construir un pipeline reproducible en local que puede migrarse a AWS real con cambios minimos. El enfoque en latencia, automatizacion, manejo de desbalanceo y procesamiento analitico eficiente responde a los requerimientos tecnicos del mercado internacional y aplica rigor matematico en cada etapa.
REGLAS:
NO COMENTARIOS, NO DECORADORES