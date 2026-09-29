# Ferretería - Bloqueo de ventas sin inventario

Impide completar operaciones con cantidades positivas de productos almacenables cuando el almacén correspondiente no tiene disponibilidad sin reservar.

## Cobertura

- Órdenes POS: usa `pos.config.picking_type_id.warehouse_id.lot_stock_id`, muestra un bloqueo inmediato con la disponibilidad de esa sucursal y fuerza el movimiento de inventario en tiempo real.
- Pedidos de venta administrativos: usa `sale.order.warehouse_id.lot_stock_id`.
- Facturas directas: bloquea productos almacenables cuando la factura no proviene de POS o Ventas.
- Servicios y productos no almacenables: no se validan.
- Reembolsos puros: no se bloquean.

## Concurrencia

El módulo usa bloqueos consultivos transaccionales de PostgreSQL por ubicación y producto para serializar la validación de dos cajas que intenten vender la última unidad. Estos bloqueos no escriben ni corrigen `stock.quant`; el movimiento real continúa a cargo de Odoo.

## Disponibilidad y modo offline

La interfaz carga una instantánea de disponibilidad sin reservar al abrir el POS y la reduce después de cada venta aceptada o guardada localmente. La validación servidor vuelve a calcularla al aceptar la orden y es la autoridad definitiva. Si otra caja vende después de cargar la pantalla, el servidor rechaza cualquier exceso. En modo offline la advertencia local continúa descontando las ventas del mismo terminal; la orden solo queda aceptada por Odoo cuando la sincronización supera la validación servidor.
