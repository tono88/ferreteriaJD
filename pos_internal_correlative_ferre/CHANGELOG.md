# Changelog

## 18.0.1.0.13 — Recuperación estricta del POS

- Se elimina por completo la sobrescritura de `pos.order._load_pos_data_fields()`.
- Se retiran todos los assets frontend del módulo durante la recuperación.
- Se conserva únicamente la generación del correlativo en backend y su copia a la factura.
- Motivo: en Odoo 18 `pos.order` no define una lista estándar en ese método; el mixin base devuelve `[]`. Añadir solo `internal_correlative` reducía el esquema frontend de la orden y eliminaba relaciones estándar como `payment_ids`, `session_id`, `partner_id`, `lines`, `uuid` y nombre.

# 18.0.1.0.12 — 2026-07-21

- Recuperación de emergencia del POS.
- Se revierte la modificación de `_load_pos_data_fields()` que añadió manualmente `lines` y `payment_ids`.
- Se restaura el cargador original: conserva todos los campos estándar de Odoo mediante `super()` y añade únicamente `internal_correlative`.
- No se modifica `PosOrder.setup()`, `createNewOrder()`, la serialización, el cliente, la sesión, la lista de precios ni los pagos.
- Corrige órdenes nuevas con `NaN`, cliente no persistido y sincronización sin `session_id`.

# Changelog

## 18.0.1.0.6 — 2026-07-20

- Centraliza la impresión del correlativo POS con el texto `No. interno`.
- Copia `pos.order.internal_correlative` a la factura desde `_prepare_invoice_vals`.
- Refuerza la sincronización después de generar la factura.
- Actualiza los parches JavaScript al modelo `PosOrder` de Odoo 18.
- Elimina del bundle los templates antiguos que podían sustituir o duplicar la referencia de orden.
