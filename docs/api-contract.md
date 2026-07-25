# API Contract - Clickstream Pipeline

## Endpoint
```
POST /events
Content-Type: application/json
```

## Event Types
- `heartbeat` - Periodico (250ms) en cart/checkout con items
- `page_view` - Al entrar a cart/checkout/catalog
- `add_to_cart` - Agregar producto al carrito
- `remove_from_cart` - Quitar producto del carrito
- `view_product` - Ver detalle de producto
- `start_checkout` - Iniciar checkout
- `purchase` - Compra completada
- `abandon` - Abandono de carrito (razon o cerrar ventana)

## Payload Base (todos los eventos)
```json
{
  "event_type": "string",
  "timestamp": "ISO8601 UTC",
  "session_id": "uuid-v4",
  "user_id": "uuid-v4",
  "mouse_click_count": "integer"
}
```

## Payload por Evento

### heartbeat
```json
{
  "event_type": "heartbeat",
  "timestamp": "2026-07-24T18:30:00.000Z",
  "session_id": "uuid",
  "user_id": "uuid",
  "mouse_click_count": 15,
  "page": "cart|checkout",
  "cart_value": 1200.50,
  "product_count": 3,
  "product_quantities": { "prod_001": 2, "prod_003": 1 },
  "shipping_option_selected": "standard|express|store",
  "mouse_x": 320,
  "mouse_y": 180
}
```

### page_view
```json
{
  "event_type": "page_view",
  "timestamp": "2026-07-24T18:30:00.000Z",
  "session_id": "uuid",
  "user_id": "uuid",
  "mouse_click_count": 5,
  "page": "cart|checkout|catalog",
  "cart_value": 1200.50,
  "product_count": 3,
  "product_quantities": { "prod_001": 2, "prod_003": 1 },
  "shipping_option_selected": "standard|express|store"
}
```

### add_to_cart
```json
{
  "event_type": "add_to_cart",
  "timestamp": "2026-07-24T18:30:00.000Z",
  "session_id": "uuid",
  "user_id": "uuid",
  "mouse_click_count": 8,
  "product_id": "prod_002",
  "category": "perifericos",
  "price": 85,
  "cart_value": 1285.50,
  "product_count": 3,
  "product_quantities": { "prod_001": 2, "prod_002": 1, "prod_003": 1 },
  "shipping_option_selected": "standard|express|store"
}
```

### remove_from_cart
```json
{
  "event_type": "remove_from_cart",
  "timestamp": "2026-07-24T18:30:00.000Z",
  "session_id": "uuid",
  "user_id": "uuid",
  "mouse_click_count": 10,
  "cart_value": 1200.50,
  "product_count": 2,
  "product_quantities": { "prod_001": 2, "prod_003": 1 },
  "shipping_option_selected": "standard|express|store"
}
```

### view_product
```json
{
  "event_type": "view_product",
  "timestamp": "2026-07-24T18:30:00.000Z",
  "session_id": "uuid",
  "user_id": "uuid",
  "mouse_click_count": 3,
  "product_id": "prod_005",
  "category": "audio",
  "price": 95
}
```

### start_checkout
```json
{
  "event_type": "start_checkout",
  "timestamp": "2026-07-24T18:30:00.000Z",
  "session_id": "uuid",
  "user_id": "uuid",
  "mouse_click_count": 12,
  "page": "checkout",
  "cart_value": 1200.50,
  "product_count": 3,
  "product_quantities": { "prod_001": 2, "prod_003": 1 },
  "payment_method_selected": null,
  "shipping_option_selected": "standard|express|store"
}
```

### purchase
```json
{
  "event_type": "purchase",
  "timestamp": "2026-07-24T18:30:00.000Z",
  "session_id": "uuid",
  "user_id": "uuid",
  "mouse_click_count": 15,
  "cart_value": 1200.50,
  "product_count": 3,
  "product_quantities": { "prod_001": 2, "prod_003": 1 },
  "payment_method_selected": "credit_card|debit_card|cash",
  "shipping_option_selected": "standard|express|store"
}
```

### abandon
```json
{
  "event_type": "abandon",
  "timestamp": "2026-07-24T18:30:00.000Z",
  "session_id": "uuid",
  "user_id": "uuid",
  "mouse_click_count": 8,
  "cart_value": 1200.50,
  "product_count": 3,
  "product_quantities": { "prod_001": 2, "prod_003": 1 },
  "shipping_option_selected": "standard|express|store",
  "abandon_reason": "Costo de envio muy alto|Encontre mejor precio|No estoy listo|Solo estaba mirando|El total es muy alto|Prefiero recoger en tienda pero no hay cerca|Me preocupa el tiempo de entrega|cerro ventana"
}
```

## Reglas de Tracking (Frontend)
- Solo envia eventos si `page` en `["cart", "checkout"]` AND `carrito.length > 0`
- Eventos en `catalog` se bufferizan y flush al entrar a cart/checkout con items
- Heartbeat cada 250ms (configurable via `config.js`)
- `beforeunload` envia `abandon` via `navigator.sendBeacon` si tracking activo

## Configuracion (config.js - generado por Terraform)
```javascript
window.CLICKSTREAM_CONFIG = {
  apiUrl: "https://xxx.execute-api.us-east-1.amazonaws.com/prod/events",
  trackedPages: ["cart", "checkout"],
  heartbeatIntervalMs: 250
};
```

## Notas para Lambda
- **NO** calcular velocity, distance, idle en frontend - solo datos crudos
- Lambda calcula features derivadas desde `mouse_x`, `mouse_y`, `timestamp` consecutivos
- `product_quantities` es objeto `{product_id: quantity}`
- `shipping_option_selected`: `store` para recojo en tienda, sino `standard|express`
- `payment_method_selected`: solo en `purchase` y `start_checkout` (null en start_checkout)
- `abandon_reason`: solo en `abandon`