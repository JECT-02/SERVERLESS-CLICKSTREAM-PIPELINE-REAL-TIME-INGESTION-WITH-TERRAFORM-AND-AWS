# Bitacora 2 - Conexion Frontend a API Gateway
**Fecha:** 2026-07-25
**Version:** 1.0
**Proyecto:** Serverless Clickstream Pipeline - Real-Time Event Ingestion with Terraform & Polars

---

## Implementacion: Envio de Eventos desde Frontend a API Gateway

### Arquitectura de Comunicacion

El frontend (`frontend/index.html`) envia eventos de clickstream al backend via HTTP POST hacia el endpoint de API Gateway. La comunicacion es sincrona via `fetch()` para eventos en tiempo real, con `sendBeacon()` como fallback para abandono de pagina.

### URL de API Gateway (Configuracion Dinamica)

El frontend obtiene la URL del endpoint desde `window.CLICKSTREAM_CONFIG`, definido en `frontend/config.js`. Este archivo es generado automaticamente por Terraform tras `terraform apply` mediante el recurso `local_file`:

```
frontend/config.js
  -> window.CLICKSTREAM_CONFIG = {
       apiUrl: "http://localhost:4566/restapis/{api-id}/prod/_user_request_/events",
       trackedPages: ["cart", "checkout"],
       heartbeatIntervalMs: 250
     }
```

En desarrollo sin Terraform, existe un fallback hardcodeado en `index.html`:
```javascript
const CONFIG = window.CLICKSTREAM_CONFIG || {
  apiUrl: "http://localhost:4566/restapis/ID_API/STAGE/events",
  trackedPages: ["cart", "checkout"],
  heartbeatIntervalMs: 250
};
```

### Mecanismo de Envio

Existen dos mecanismos de envio:

**1. `fetch()` (principal)**
- Funcion `sendEventNow(event)` en linea 144
- Realiza `fetch(API_URL, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(event) })`
- Si `res.ok`, parsea JSON y verifica `trigger_retention` para mostrar modal
- Si falla (offline/sin servidor), registra el evento y continua sin error

**2. `sendBeacon()` (abandono de pagina)**
- Event listener `beforeunload` en linea 591
- Si tracking activo y hay items en carrito, envia evento `abandon` via `navigator.sendBeacon(API_URL, JSON.stringify(...))`
- Fire-and-forget: no espera respuesta

### Reglas de Tracking (Compuerta de Envio)

La funcion `shouldTrack()` (linea 125) determina si un evento debe enviarse inmediatamente o almacenarse en buffer:

```javascript
function shouldTrack() {
  if (!TRACKED_PAGES.has(currentPage)) return false;   // Solo cart y checkout
  if (currentPage === "cart" && carrito.length === 0) return false;
  if (currentPage === "checkout" && carrito.length === 0) return false;
  return true;
}
```

**Logica:**
- Solo se rastrean las paginas `cart` y `checkout`
- El carrito debe tener al menos 1 item
- Pagina `catalog` nunca se rastrea en tiempo real (usa buffer)

### Buffer de Eventos en Catalogo

Cuando el usuario esta en `catalog` (pagina no rastreada), los eventos se acumulan en un buffer para evitar ruido en la API:

- **Buffer**: `let eventBuffer = []` (linea 120, maximo 100 eventos, evicta los mas viejos)
- **`bufferEvent(event)`** (linea 139): agrega al buffer con limite de 100
- **`flushEventBuffer()`** (linea 132): toma snapshot, limpia buffer, envia cada evento via `sendEvent()`
- **Flush triggers**: al entrar a `cart` (`renderCart()`) o `checkout` (`goToCheckout()`)

Flujo:
```
Usuario en catalog
  -> view_product / add_to_cart -> bufferEvent() -> BUFFER

Usuario navega a cart (con items > 0)
  -> flushEventBuffer()
  -> sendEvent(page_view)
  -> sendEvent(add_to_cart)  // eventos acumulados
  -> startHeartbeat()
```

### Heartbeat Periodico

Mientras el usuario esta en `cart` o `checkout` con items, se envia un heartbeat cada 250ms:

- **Intervalo**: `HEARTBEAT_INTERVAL_MS = 250` (4 heartbeats/segundo)
- **`startHeartbeat()`** (linea 175): detiene heartbeat anterior, inicia nuevo setInterval
- **`stopHeartbeat()`** (linea 181): limpia el intervalo
- **`sendHeartbeat()`** (linea 287): verifica `shouldTrack()`, envia `makeEvent("heartbeat")`

**Inicio de heartbeat:**
- `renderCart()` cuando cart se renderiza
- `goToCheckout()` cuando se navega a checkout

**Detencion de heartbeat:**
- `renderCatalogo()` al volver a catalogo
- `renderCart()` cuando carrito queda vacio
- `confirmCheckout()` tras compra exitosa
- `abandonCart()` tras abandono

### Payload de Eventos (Datos Crudos, Sin Calculos en Frontend)

Cada evento se construye via `makeEvent(eventType, extra)` (linea 214). Todos incluyen campos base:

| Campo | Fuente | Descripcion |
|-------|--------|-------------|
| `event_type` | Parametro | Tipo de evento |
| `timestamp` | `new Date().toISOString()` | Marca de tiempo UTC |
| `session_id` | `crypto.randomUUID()` | Identificador de sesion (generado al cargar) |
| `user_id` | `localStorage.getItem("userId")` o `crypto.randomUUID()` | Identificador de usuario (persistente) |
| `mouse_click_count` | Contador global | Incrementado en cada `click` |

**Campos adicionales por tipo de evento:**

| event_type | Campos extra |
|------------|-------------|
| `heartbeat` | `page`, `cart_value`, `product_count`, `product_quantities`, `shipping_option_selected`, `mouse_x`, `mouse_y` |
| `page_view` | `page`, `cart_value`, `product_count`, `product_quantities`, `shipping_option_selected` |
| `add_to_cart` | `product_id`, `category`, `price`, `cart_value`, `product_count`, `product_quantities`, `shipping_option_selected` |
| `remove_from_cart` | `cart_value`, `product_count`, `product_quantities`, `shipping_option_selected` |
| `start_checkout` | `page=checkout`, `cart_value`, `product_count`, `product_quantities`, `payment_method_selected`, `shipping_option_selected` |
| `purchase` | `cart_value`, `product_count`, `product_quantities`, `payment_method_selected`, `shipping_option_selected` |
| `abandon` | `cart_value`, `product_count`, `product_quantities`, `shipping_option_selected`, `abandon_reason` |
| `view_product` | `product_id`, `category`, `price` |

### Datos de Mouse (Tiempo Real)

- **`mouse_x` / `mouse_y`**: actualizados en cada `mousemove` (linea 601) con `e.clientX` y `e.clientY`
- **`mouse_click_count`**: incrementado en cada `click` (linea 600)
- Enviados en crudo (sin calcular velocidad ni idle en frontend). El calculo de features derivadas se realiza en Lambda.

### Manejo de Respuesta: Modales de Retencion

Cuando la Lambda responde con `trigger_retention: true`, el frontend muestra un modal de retencion segun `retention_type`:

| retention_type | Modal | Accion al aceptar |
|---------------|-------|-------------------|
| `shipping_discount` | "Envio gratis para ti!" | Aplica envio gratuito (`shippingType = "standard"`) |
| `express_upgrade` | "Upgrade a Express gratis!" | Cambia a envio express (`shippingType = "express"`) |
| `coupon` (default) | "No te vayas! Cupon: SAVE10" | Muestra codigo de cupon |

### Modal de Abandono

Al hacer clic en "Abandonar carrito", se muestra modal con razones predefinidas. Al seleccionar una, se envia evento `abandon` con `abandon_reason`.

### Pruebas Unitarias (Frontend)

22 tests en `frontend/tests/`:
- **tracking.test.js** (13 tests): validacion de schemas raw por tipo de evento, reglas de tracking (shouldTrack, buffer, flush)
- **api-connection.test.js** (9 tests): validacion de payloads enviados, headers, manejo de errores HTTP

### Archivos Relacionados

- `frontend/index.html` - implementacion completa del frontend (606 lineas)
- `frontend/config.js` - configuracion generada por Terraform (URL, paginas rastreadas, intervalo heartbeat)
- `frontend/tests/tracking.test.js` - tests de reglas de tracking
- `frontend/tests/api-connection.test.js` - tests de conexion con API
- `infra/environments/local/main.tf` - recurso `local_file` que genera config.js
