# Diagnóstico, despliegue y verificación — 18.0.1.5.1

**Único entorno autorizado para actualización/prueba:** `COPIA_PRDO_CUIDADO`. No tocar producción.

## Evidencia recibida

- Ana Lucía figura como integrante del grupo `Lectura global de órdenes POS` y la lectura global de `pos.order` funciona.
- La interfaz seguía mostrando un `Many2one` con `Buscar más...` solo para JB Central.
- Aplicaciones muestra `Versión más reciente = 18.0.1.5.0`, lo cual NO acredita por sí solo que la vista XML haya sido aplicada en la base.

## Corrección incluida

En la vista XML original, la visibilidad se controlaba mediante `can_select_global_pos` (compute). Ahora se controla por atributos de grupo a nivel de vista:

- `pos_config_id` solamente para **usuarios sin** `ferreteria_user_scope_ferre.group_pos_global_order_read`.
- `global_pos_config_id` solamente para **usuarios con** ese grupo.

Se mantienen ambos campos y todos los métodos Python de `18.0.1.5.0`. El indicador calculado sigue en el modelo por compatibilidad, pero ya no decide la interfaz.

## Pasos de instalación

1. Identificar inequívocamente la base, runtime, puerto y addons_path de `COPIA_PRDO_CUIDADO`; `localhost:8069` no confirma que sea la copia.
2. Hacer respaldo de la copia (base + filestore); no instalar ni actualizar otro módulo.
3. Sustituir exclusivamente la carpeta `pos_sales_summary_report_ferre` del runtime de la copia. Conservar copia del código `18.0.1.5.0` para rollback.
4. Reiniciar únicamente el Odoo de la copia; actualizar la lista de aplicaciones si corresponde; ejecutar **Actualizar** sobre `pos_sales_summary_report_ferre`.
5. Cerrar sesión y volver a iniciar sesión con Ana y con Yumari por separado; evitar sessiones como administrador. Comprobar la vista efectiva, no solo la versión del manifiesto.
6. Probar catálogo, filtros de POS, global vacío, PDF/XLSX, totales y operación restringida. Documentar PASS/FAIL reales.

## Diagnóstico solo lectura en Odoo Shell de la copia

Con la conexión a la DB correcta, ejecutar el script `DIAGNOSTICO_SELECTOR_READONLY_ODOO_SHELL.py` incluido en `docs`. No requiere instalación y no hace escrituras.

Interpretación:
- `installed_version` menor a `18.0.1.5.1` o XML de DB sin `global_pos_config_id`: el módulo no se actualizó realmente.
- Grupo para Ana `False` o `get_view` sin selector global: investigar grupo/XML-ID o vista heredada.
- Si se usa la sesión de administrador y no la de Ana, la evidencia no demuestra el resultado para Ana.

## Regresión obligatoria

1. Ana ve todos los POS activos de compañías autorizadas en selector de reporte.
2. POS vacío: órdenes globales, respetando lectura del usuario.
3. JBC solo JBC, Taxisco solo Taxisco, Palinche solo Palinche.
4. PDF y XLSX conservan fechas, líneas, correlativos, reembolsos y totales.
5. Con órdenes reales de Taxisco y Palinche, comparar `order.payment_ids` bajo Ana contra pagos técnicos de referencia; **no asumir** efecto de `pos.payment`.
6. Ana mantiene operación solo JBC y no puede abrir Taxisco/Palinche.
7. Yumari sin grupo global mantiene selector y operación solo Palinche.
8. Comprobar invariancia de `ferreteria_allowed_pos_ids`, reglas de `pos.config`, `pos.order`, `pos.payment` y derechos de escritura.
9. Rechazar ID forjado de POS no autorizado en llamada directa a reporte.

La corrección sigue siendo **candidata** hasta completar pruebas funcionales en la copia.
