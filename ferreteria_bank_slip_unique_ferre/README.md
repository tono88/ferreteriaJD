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

## Instalación

La instalación revisa las referencias existentes en `account.payment`. Si encuentra duplicados, aborta y muestra los pagos que deben corregirse antes de volver a instalar.
