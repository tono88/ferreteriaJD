# Prueba de la corrección de lectura de pagos — 18.0.1.5.2

**Entorno permitido:** únicamente `COPIA_PRDO_CUIDADO`. No actualizar ni modificar `FERRE_PROD` ni producción publicada.

## Hipótesis que se debe reproducir ANTES de promover

- `pos.order` es legible globalmente por Ana gracias a `ferreteria_user_scope_ferre.group_pos_global_order_read`.
- `pos.payment` conserva un `ir.rule` global que permite leer solo los pagos de sus POS operativos (JBC).
- El reporte 18.0.1.5.1 descarta explícitamente la orden si pagos visibles `contado` y `credito` son ambos cero; por ello pierde órdenes de otros POS.

El script `DIAGNOSTICO_PAGOS_COPIA_PRDO_CUIDADO.py` permite contrastar, sin escrituras, el conjunto de pagos visibles por Ana y el conjunto técnico real de órdenes ya autorizadas. Cambie en el script DATE_FROM/DATE_TO al mismo rango de fechas del reporte.

**No se ejecutó ese script contra la copia desde el entorno de generación de este ZIP.** Su salida debe anexarse a la validación real antes de aprobar el módulo.

## Aplicación candidata en la copia

1. Confirmar que el servicio y la base de datos apuntan inequívocamente a `COPIA_PRDO_CUIDADO`. `localhost:8069` NO garantiza identidad; verificar configuración `db_name`/`dbfilter` o banner Odoo.
2. Generar respaldo de base y filestore y asegurar reversión a 18.0.1.5.1.
3. Ejecutar el diagnóstico read-only sobre la versión instalada 18.0.1.5.1 y guardar salida.
4. Si se confirma pérdida de pagos de otros POS, reemplazar exclusivamente el addon `pos_sales_summary_report_ferre` por el contenido de esta versión.
5. Reiniciar exclusivamente el servicio Odoo de la copia, actualizar la lista de aplicaciones si es necesario y pulsar **Actualizar** sobre el reporte. **NO** actualizar `ferreteria_user_scope_ferre`.
6. Limpiar sesión de navegación, volver a iniciar como Ana.

## Pruebas obligatorias

- [ ] Ana conserva grupo de lectura global y scope operativo solo JBC.
- [ ] Selector de reporte incluye JBC, Taxisco, Palinche y los demás POS de compañía autorizada.
- [ ] POS vacío incluye órdenes reales de JBC, Taxisco y Palinche en el mismo rango con datos.
- [ ] JBC seleccionado muestra solo órdenes JBC.
- [ ] Taxisco seleccionado muestra solo órdenes Taxisco.
- [ ] Palinche seleccionado muestra solo órdenes Palinche.
- [ ] Dos órdenes de sucursales distintas aparecen con sus importes de contado, otros, total y correlativos reales.
- [ ] Facturación todos / facturadas / no facturadas respeta el filtro.
- [ ] PDF mantiene presentación, fechas, FEL, cliente y totales.
- [ ] XLSX contiene exactamente el mismo conjunto e importes que el PDF.
- [ ] Reembolsos se filtran como en 18.0.1.5.1.
- [ ] Ana solo ve y opera JBC en el tablero POS, no puede abrir otros POS.
- [ ] Yumari sin grupo global sigue seleccionando únicamente Palinche y sin regresiones.
- [ ] `ferreteria_allowed_pos_ids` y reglas `pos.config`, `pos.order`, `pos.payment` no han cambiado.
- [ ] Prueba de intento de filtro con POS de otra compañía: AccessError.

## Delimitación de seguridad

- Las órdenes se consultan con `self.env['pos.order'].search()` (sin `sudo`).
- Solamente si el usuario posee `group_pos_global_order_read`, el reporte obtiene pagos vía `self.env['pos.payment'].sudo().search()` en una única consulta restringida por **IDs concretos de órdenes ya legibles** y **compañías autorizadas**.
- Para usuarios normales se mantiene el acceso a `order.payment_ids` ordinario, sin `sudo`.
- La elevación no crea ninguna acción de pago, no cambia configuración POS y no expone un nuevo menú ni modelo persistente.
- PDF y Excel reutilizan el mismo `_get_report_values()` y su clasificación habitual contado/otros.

## Estado

- Verificación de sintaxis, XML y pruebas con dobles Odoo: ejecutadas localmente.
- Pruebas reales de `COPIA_PRDO_CUIDADO`, importes e impresión: **PENDIENTES**.
- Promoción a producción: **NO AUTORIZADA**.
