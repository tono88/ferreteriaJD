# Ferretería - Bloqueo de ventas sin inventario

Impide completar operaciones con cantidades positivas de productos almacenables cuando el almacén correspondiente no tiene disponibilidad sin reservar.

## Cobertura

- Órdenes POS: usa `pos.config.picking_type_id.warehouse_id.lot_stock_id` y fuerza el movimiento de inventario en tiempo real.
- Pedidos de venta administrativos: usa `sale.order.warehouse_id.lot_stock_id`.
- Facturas directas: bloquea productos almacenables cuando la factura no proviene de POS o Ventas.
- Servicios y productos no almacenables: no se validan.
- Reembolsos puros: no se bloquean.

## Concurrencia

El módulo usa bloqueos consultivos transaccionales de PostgreSQL por ubicación y producto para serializar la validación de dos cajas que intenten vender la última unidad. Estos bloqueos no escriben ni corrigen `stock.quant`; el movimiento real continúa a cargo de Odoo.
