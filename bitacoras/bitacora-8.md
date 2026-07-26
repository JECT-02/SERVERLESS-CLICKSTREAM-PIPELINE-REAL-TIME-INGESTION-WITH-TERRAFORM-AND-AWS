# Bitacora 8 - Generacion de Data Sintetica Realista
**Fecha:** 2026-07-25
**Proyecto:** Serverless Clickstream Pipeline - Real-Time Event Ingestion with Terraform & Polars

---

## Cambios Realizados

### Script de generacion: `data/generate_sessions.py`

Generador de sesiones de clickstream con comportamiento realista basado en estudios de abandono de carrito (Baymard Institute, Weisgarber et al. 2025, Abhichandani & Vadrevu 2025).

### Arquitectura del generador

| Componente | Descripcion |
|------------|-------------|
| `MousePath` | Genera trayectorias de mouse por zonas (cart, checkout, exit). Bezier con ruido para abandoners, lineal para purchasers |
| `SessionGenerator` | Maquina de estados: cart heartbeats → add/remove → start_checkout → shipping toggles → abandon/purchase |
| `compute_session_features` | Calcula features identicas a `features.py`: velocity, idle, acceleration, dwell, exit intent |
| `inject_anomaly_events` | Anade outliers (5%), precios negativos (3%), mouse en 0,0 (3%), timestamps desordenados (2%) |

### Arquetipos de sesion

| Tipo | % | Comportamiento del mouse |
|------|---|--------------------------|
| **Abandoner** | ~70% | Velocidad decreciente, idle creciente, exit intent al final, shipping switches, page regressions |
| **Purchaser** | ~30% | Velocidad estable, idle bajo, trayectorias directas, pocos cambios de shipping |

### Asignacion de abandono (no aleatoria)

Score compuesto por 6 seniales con pesos:

| Senial | Peso |
|--------|------|
| Velocity trend decreciente | 25% |
| Idle ratio > 30% | 25% |
| Page regressions >= 2 | 20% |
| Shipping switches >= 2 | 15% |
| Exit intent >= 2 | 10% |
| Cart removals > additions | 5% |

Ruido gaussiano N(0, 0.08). Threshold 0.50. Abandon rate resultante: **69.3%** (coherente con Baymard 70.22%).

### Outputs generados

| Ruta | Contenido |
|------|-----------|
| `data/raw/YYYY/MM/DD/` | 187,478 JSONs individuales (mismo formato que Lambda) |
| `data/processed/sessions.parquet` | 5,000 filas, 30 columnas (features + target) |
| `data/metadata/generation_report.json` | Estadisticas de generacion |

### Campos en cada JSON

- **Comunes:** event_type, timestamp, session_id, user_id, mouse_click_count, device
- **Heartbeat:** page, cart_value, product_count, product_quantities, shipping_option_selected, mouse_x, mouse_y
- **add_to_cart:** product_id, category, price + comunes de carrito
- **remove_from_cart:** comunes de carrito
- **start_checkout:** page=checkout, payment_method_selected=null
- **purchase:** payment_method_selected + comunes
- **abandon:** abandon_reason + comunes

### Feature columns en Parquet (30 columnas)

`velocity_avg`, `velocity_max`, `velocity_std`, `acceleration_avg`, `acceleration_max`, `idle_total_ms`, `distance_total`, `velocity_trend`, `exit_intent_count`, `dwell_total_ms`, `dwell_segments`, `click_frequency`, `session_duration_s`, `cart_delta`, `product_removals`, `product_additions`, `shipping_switches`, `page_regression_count`, `payment_hesitation_ms`, `payment_method_switches`, `event_count`, `has_checkout`, `abandon_reason`, `payment_method`, `device`, `abandoned` (target)

`abandoned=1`: 3,465 sesiones (69.3%)
`abandoned=0`: 1,535 sesiones (30.7%)

### Bugs corregidos durante generacion

1. **Timestamp anomaly usaba `now()` en vez de session base** → causaba session_duration_s de 8+ horas. Corregido a usar `ref_ts + session_duration + 2-10min`.
2. **dt_s sin capping** → idle_total_ms acumulaba 29M ms. Corregido: `dt_s > 10s → 0.25s`.
3. **mouse_x/mouse_y = None en anomalias** → TypeError en calculo de features. Corregido: usar 0 en vez de None + `safe_mouse()`.
