# Ferretería - Boleta bancaria única

Impide reutilizar un número de boleta bancaria dentro de la misma compañía entre:

- `account.payment.bank_reference`;
- `pos.order.payment.bank_slip_number`;
- `pos.order.payment.master.bank_slip_number`.

La comparación elimina espacios externos, normaliza Unicode y no distingue mayúsculas/minúsculas. Los registros históricos no se liberan al cancelar, eliminar o editar un pago.

## Mejora 18.0.1.1.0: una boleta por operación de registro

El asistente estándar de registrar pagos puede crear varios pagos al seleccionar
facturas de distintos clientes o desactivar «Agrupar pagos». Ahora esos pagos
pueden compartir la boleta indicada en una sola confirmación del asistente.
Antes, el segundo pago chocaba con el primero y toda la operación se revertía,
mostrando una boleta utilizada en «Pago /» que luego no aparecía en el listado.

Se mantiene una única reserva por compañía y número normalizado, con una relación
a los pagos de esa operación. Otra confirmación, un pago manual o un pago POS no
pueden reutilizarla. Las reservas históricas anteriores permanecen intactas.
Esto no libera boletas antiguas ni permite agrupar pagos ya existentes.

### Actualización

1. Haz un respaldo y prueba primero en una copia de la base de datos.
2. Despliega esta versión del módulo y detén los procesos Odoo antes de actualizar.
3. Ejecuta con la configuración del servidor:
   `odoo-bin -c /ruta/odoo.conf -d NOMBRE_BD -u ferreteria_bank_slip_unique_ferre --stop-after-init`
4. Inicia nuevamente el servicio Odoo con todos sus procesos.

La actualización crea la relación de pagos compartidos. No requiere borrar el
historial ni reinstalar el módulo. Es un cambio Python: no se instala mediante
el importador de módulos ZIP. El complemento de columna y buscador sigue siendo
compatible y no es necesario reinstalarlo.

### Pruebas

Se incluyen pruebas Odoo para pagos de distintos clientes, referencias vacías,
reutilización entre operaciones, escritura posterior en los miembros del grupo,
conservación del historial y rechazo de contextos RPC que intenten saltarse la
validación. Ejecutar en una base de pruebas con las dependencias instaladas:
`odoo-bin -c /ruta/odoo.conf -d BD_PRUEBAS -u ferreteria_bank_slip_unique_ferre --test-enable --test-tags /ferreteria_bank_slip_unique_ferre --stop-after-init`

## Recuperación de boletas anuladas — 18.0.1.2.0

Cancelar o eliminar un pago no elimina su reserva histórica. Por ello una boleta
puede bloquearse aunque no aparezca al buscar pagos. Antes no existía un mecanismo
para corregir una operación anulada: el error seguía mostrando el nombre del
pago original, incluso cuando este había sido eliminado.

Un administrador contable o de sistema puede ahora registrar la operación
corregida desde el asistente de pagos:

1. Seleccionar las facturas pendientes y abrir **Pagar**.
2. Indicar diario, método, fecha y número real de boleta.
3. Marcar **Recuperar boleta anulada** y explicar el motivo.
4. Confirmar los pagos.

La recuperación solo procede si todos los pagos asociados anteriores están
cancelados o ya no existen y ningún otro pago activo usa la misma referencia.
No permite recuperar reservas POS. La reserva se bloquea durante la operación,
conserva su identificador y guarda un historial con origen anterior, usuario,
fecha, motivo y pagos sustitutos. La operación completa se revierte si falla.
Los pagos cancelados sustituidos no pueden volver a publicarse con esa boleta.
Sin marcar la recuperación, la política histórica continúa igual.

Actualizar el módulo y reiniciar todos los procesos Odoo como se describe arriba.
Esta versión agrega un campo JSON de auditoría; no borra reservas existentes.

## Instalación

La instalación revisa las referencias existentes en `account.payment`. Si encuentra duplicados, aborta y muestra los pagos que deben corregirse antes de volver a instalar.

### Compatibilidad con el verificador de duplicados anterior

El módulo opcional `payment_bank_reference_dup_check` devuelve una ventana en
lugar de publicar el pago cuando ve referencias repetidas dentro del mismo lote.
El asistente estándar ignora esa acción y puede dejar asientos en borrador.
Esta versión aplica la reserva histórica como control principal y omite únicamente
el aviso antiguo durante la publicación; las operaciones distintas siguen
bloqueadas por la reserva SQL. También revierte el registro si algún asiento
generado no quedó publicado. No fuerza saldos ni estados de las facturas.
