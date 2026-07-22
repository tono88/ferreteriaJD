# Changelog

## 18.0.1.0.1 — 2026-07-21

- Corrige el error de instalación `Many2many fields SaleOrder.transaction_ids ... use the same table and columns`.
- Sustituye la herencia ORM múltiple de `sale.order` y `pos.order` por herencia de extensión simple.
- Convierte el validador compartido en funciones Python auxiliares para evitar duplicar campos relacionales estándar durante la creación del registro de Odoo.
- No cambia la regla funcional de bloqueo de inventario.

## 18.0.1.0.0 — 2026-07-20

- Primera versión.
- Validación servidor para órdenes POS antes de pago, facturación y entrega.
- Creación de picking POS en tiempo real para impedir que sesiones con descuento diferido reutilicen existencias ya vendidas.
- Resolución obligatoria de almacén mediante `pos.config.picking_type_id.warehouse_id`.
- Validación de pedidos administrativos por almacén.
- Bloqueo de facturas directas de productos almacenables sin origen POS/Ventas.
- Exclusión de servicios, productos no almacenables y reembolsos puros.
- Bloqueo transaccional por ubicación/producto para proteger ventas concurrentes.
