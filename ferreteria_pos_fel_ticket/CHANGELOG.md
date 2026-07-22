# Changelog

## 18.0.1.0.2 — 2026-07-21

- Muestra `No. interno` en el recibo POS de ventas sin factura FEL.
- Reutiliza el correlativo obtenido desde `get_fel_ticket_data_for_pos`.
- No modifica `PosOrder`, la creación de órdenes, clientes, pagos, líneas, listas de precios ni IndexedDB.
- Conserva sin cambios la presentación del recibo FEL facturado.

## 18.0.1.0.1 — 2026-07-20

- Añade `No. interno` al recibo POS FEL.
- Añade `No. interno` al ticket térmico PDF del backend.
- Mantiene el dato visible también en comprobantes sin factura FEL.
- Declara dependencia explícita de `pos_internal_correlative_ferre`.
