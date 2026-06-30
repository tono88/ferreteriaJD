# vlf_dashboard_reports — Entrega 1

Extensión para Odoo 18 Community del módulo `vlf_dashboard_pro`.

## Alcance

- Dashboard **Ventas Generales**: POS + ventas administrativas, sin sumar facturas como una segunda venta.
- Dashboard **Punto de Venta**: operación exclusiva de POS.
- Dashboard **Ejecutivo Gerencial**: ventas operativas separadas de facturación financiera.
- Base de consulta `vlf.sales.order.fact` con drill-down al documento origen.
- Devoluciones POS mediante órdenes negativas.
- Notas de crédito administrativas publicadas vinculadas a líneas de venta y no originadas en POS.
- Sucursal determinada por `sale.order.warehouse_id` o `pos.config.warehouse_id`.
- Fechas finales inclusivas para campos Datetime.
- Compañía fija en backend y selector oculto en la interfaz.
- `stock.quant` limitado a ubicaciones internas en el motor genérico.
- Totales acumulados y agregaciones genéricas corregidos.

## Regla de no duplicidad

Las ventas operativas provienen de `sale.order` y `pos.order`. Las facturas de cliente no crean una segunda fila operativa. La facturación se consulta como indicador financiero separado.

## Instalación

1. Mantener instalado `vlf_dashboard_pro`.
2. Copiar `vlf_dashboard_reports` dentro de la ruta de addons personalizados.
3. Reiniciar Odoo.
4. Activar modo desarrollador y actualizar la lista de aplicaciones.
5. Instalar **Tecnodyne Dashboard Reports - Ferretería**.
6. Abrir **Tecnodyne Dashboards → Configuración → Actualizar dashboards predeterminados** si se requiere regenerar presets.

## Pruebas funcionales mínimas

1. Venta POS sin factura.
2. Venta POS facturada: debe contarse una sola vez en ventas operativas.
3. Venta administrativa confirmada.
4. Venta administrativa facturada: debe seguir contándose una sola vez.
5. Devolución POS.
6. Nota de crédito administrativa vinculada a una orden de venta.
7. Operaciones en dos sucursales/POS distintos.
8. Filtro con fecha final que incluya operaciones realizadas durante todo ese día.

## Limitaciones de esta entrega

- Todavía no incluye PDF QWeb ni XLSX formal.
- La seguridad específica por sucursal se implementará en una fase posterior cuando se conecte con el módulo real de permisos de la ferretería.
- Si una nota de crédito administrativa contiene líneas de varias bodegas, el resumen de la nota se asigna a la primera bodega vinculada. El total global no se altera.


## Moneda y filtros

Los importes de Ventas, POS y devoluciones se normalizan a la moneda de la compañía usando la tasa almacenada en cada orden. Los filtros de sucursal, punto de venta y vendedor se presentan como listas; el cliente admite búsqueda por nombre o ID.


## Criterio de importes de esta entrega

Los KPI monetarios se presentan en la moneda de la compañía e **incluyen impuestos**. Para las ventas positivas, la venta bruta se define como total cobrado más descuento antes de impuestos; la venta neta operativa corresponde al total cobrado menos las devoluciones registradas. El detalle conserva subtotal, impuestos, descuentos y devoluciones como columnas separadas.
