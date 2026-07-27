# Bitacora 14 - Ofertas de Retencion: Express con Descuento y Envio Gratis
**Proyecto:** Serverless Clickstream Pipeline - Real-Time Event Ingestion with Terraform & Polars

## Cambios Realizados

### ECS inference.py: nueva logica de retencion

`select_retention_type()` ahora usa solo `shipping_type` para decidir:

| shipping_type | retention_type | Oferta |
|---------------|----------------|--------|
| `express` | `express_discount` | Express al precio de envio normal |
| `standard` | `free_shipping` | Envio totalmente gratuito |

### Frontend: modal y aplicacion de descuento

- Nueva variable `shippingDiscount` — descuento en dolares sobre envio
- `getShippingCost()` incorpora descuento: `max(0, costo - shippingDiscount)`
- `express_discount`: modal azul "Express con descuento!", al aceptar descuenta diferencia express vs standard
- `free_shipping`: modal verde "Envio gratis para ti!", al aceptar descuenta el costo total de envio
- `shippingDiscount` se resetea al cambiar tipo envio, delivery, comprar o abandonar

### Tests actualizados

`test_select_retention_type_free_shipping` y `test_select_retention_type_express_discount` — 8/8 pasando.

### Flujo completo

```
Modelo detecta posible abandono (probability >= 0.7)
  -> ECS retorna retention_type
  -> Frontend muestra modal segun tipo
  -> Usuario acepta
  -> shippingDiscount se calcula y aplica al precio mostrado
  -> Usuario ve el nuevo total con descuento
```
