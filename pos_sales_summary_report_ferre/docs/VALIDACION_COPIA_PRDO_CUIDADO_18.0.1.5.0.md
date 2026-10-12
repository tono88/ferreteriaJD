# Validación requerida — pos_sales_summary_report_ferre 18.0.1.5.0

**Ambiente exclusivo:** `COPIA_PRDO_CUIDADO`. No instalar en producción sin validación funcional.

## Cambios incluidos

- Selector de POS específico de reportes `global_pos_config_id` (Selection) para usuarios con `ferreteria_user_scope_ferre.group_pos_global_order_read`.
- Lectura `sudo()` limitada a `pos.config` (solo `id` y `name`, POS activos y compañías habilitadas en `env.companies`).
- Conserva `pos_config_id` para scoped normales, y la búsqueda de `pos.order` sin `sudo()`.
- Validación de POS en el wizard y en el modelo del reporte PDF/XLSX; rechazo de IDs ajenos/no autorizados.
- No modifica módulos de scopes, record rules, operaciones POS ni cálculos de pagos.

## Reproducción de `pos.payment` antes de tocar su lógica

**No se ha ejecutado esta prueba en una base real desde el entorno de entrega.** Antes de incorporar un ajuste de pagos, reproducir el efecto con órdenes reales.

1. Con Ana Lucía, ejecutar reporte global actual con un rango que incluya ventas efectivas de Taxisco y Palinche. Registrar importes del PDF y del XLSX.
2. Elegir una orden **pagada** con pagos POS en Taxisco y otra en Palinche, en un rango de fechas con movimientos. Si no hay tales órdenes, registrar `SIN DATOS` y no deducir que la prueba pasa.
3. Abrir Odoo Shell en `COPIA_PRDO_CUIDADO` y ejecutar **solo consultas**:

```python
from odoo import fields

ana = env['res.users'].sudo().search([
    ('login', '=', 'corpjb.atebelan@gmail.com')
], limit=1)
assert ana, 'Ana Lucía no encontrada'
assert ana.has_group('ferreteria_user_scope_ferre.group_pos_global_order_read')
companies = ana.company_ids.ids
print('Compañías de Ana:', companies)

for pos_name in ('Taxisco', 'Palinche'):
    config = env['pos.config'].sudo().search([
        ('name', '=', pos_name), ('company_id', 'in', companies)
    ], limit=1)
    assert config, 'No hay POS autorizado llamado %s' % pos_name
    candidates = env['pos.order'].sudo().search([
        ('config_id', '=', config.id),
        ('company_id', 'in', companies),
        ('state', 'in', ['paid', 'done', 'invoiced'])
    ], order='date_order desc', limit=50)
    order = next((o for o in candidates if env['pos.payment'].sudo().search_count([
        ('pos_order_id', '=', o.id), ('amount', '>', 0)
    ])), False)
    assert order, 'No existe orden POS con pagos positivos en %s' % pos_name

    visible_order = env['pos.order'].with_user(ana).with_context(
        allowed_company_ids=companies
    ).search([('id', '=', order.id)], limit=1)
    assert visible_order, 'Ana no puede leer pos.order %s' % order.id

    reference_payments = env['pos.payment'].sudo().search([
        ('pos_order_id', '=', order.id), ('amount', '>', 0)
    ])
    visible_payments = env['pos.payment'].with_user(ana).with_context(
        allowed_company_ids=companies
    ).search([('pos_order_id', '=', order.id), ('amount', '>', 0)])
    print(pos_name, 'order', order.id,
          'pagos base', reference_payments.ids,
          'pagos Ana', visible_payments.ids,
          'suma base', sum(reference_payments.mapped('amount')),
          'suma visible', sum(visible_payments.mapped('amount')),
          'total orden', order.amount_total)
    try:
        print('order.payment_ids como Ana:', visible_order.payment_ids.ids)
    except Exception as exc:
        print('ERROR lectura order.payment_ids como Ana:', repr(exc))
```

4. Ejecutar reporte PDF y XLSX para las fechas de dichas órdenes, comparando cada fila por `order_name`/`internal_correlative` con la orden real: `Contado`, `Otros` y `Total`. Si pagos de referencia positivos no son visibles, hay evidencia de que `rule_pos_payment_scope` interfiere; confirmar además la ruta que realmente usa `_split_payments` y si el método de pago está legible.
5. Registrar `POS.PAYMENT AFECTA REPORTE GLOBAL: SÍ/NO/SIN DATOS` con evidencias; **no asumir** basándose únicamente en reglas XML. Si hay efecto funcional, modificarlo exclusivamente en este módulo, y volver a ejecutar regresiones antes de promover.

## Regresión funcional mínima (14 pruebas)

| # | Prueba | Resultado pendiente |
|---|---|---|
| 1 | Ana ve JBC y demás POS activos autorizados como filtro, sin POS ajenos a compañía | PENDIENTE |
| 2 | POS vacío presenta el reporte global de órdenes visibles | PENDIENTE |
| 3 | JBC muestra únicamente JBC | PENDIENTE |
| 4 | Taxisco muestra únicamente Taxisco | PENDIENTE |
| 5 | Palinche muestra únicamente Palinche | PENDIENTE |
| 6 | PDF: fechas, correlativo, facturación, reembolsos y encabezado intactos | PENDIENTE |
| 7 | XLSX: mismas líneas y totales que el PDF | PENDIENTE |
| 8 | Contado/crédito/total de órdenes ajenas coinciden con fuente contable | PENDIENTE |
| 9 | Ana ve exclusivamente JBC en POS operativo | PENDIENTE |
| 10 | Ana no puede abrir ni operar Taxisco/Palinche | PENDIENTE |
| 11 | Yumari sin grupo global mantiene solamente Palinche como filtro | PENDIENTE |
| 12 | `ferreteria_allowed_pos_ids` de ambos usuarios sin alteraciones | PENDIENTE |
| 13 | Reglas `pos.config`, `pos.order`, `pos.payment` sin alteración | PENDIENTE |
| 14 | Ningún permiso de escritura adicional, verificado por pruebas negativas | PENDIENTE |

**Pruebas de inyección:** invocar el reportador directamente con ID de `pos.config` de compañía no habilitada; para usuarios sin grupo, enviar un ID ajeno al scope. Ambas llamadas deben rechazarse antes de la búsqueda de órdenes. Comprobar también que fechas, filtro de facturación, clientes y reembolsos sigan coincidiendo con `18.0.1.4.0`.

**Nota:** las pruebas automatizadas con dobles de Odoo evalúan solo la lógica Python y no sustituyen una instalación real, ni prueban renderizado QWeb/XLSX o accesos en PostgreSQL.
