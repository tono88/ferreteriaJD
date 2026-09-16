# Ferretería - Seguridad por POS y almacén

Módulo de Odoo 18 para activar, por usuario y de forma explícita, un ámbito operativo de POS y almacenes.

## Campos de usuario

- `ferreteria_scope_enforced`: activa las reglas globales de servidor.
- `ferreteria_allowed_pos_ids`: POS autorizados.
- `ferreteria_allowed_warehouse_ids`: almacenes autorizados.
- `ferreteria_sales_readonly`: bloquea crear, editar y eliminar pedidos y líneas de venta.

La validación exige al menos un almacén cuando el ámbito está activo y comprueba que los POS asignados pertenezcan a los almacenes permitidos. Los usuarios sin ámbito conservan el comportamiento estándar; el superusuario conserva el bypass nativo de reglas.

## Cobertura

- POS: configuración, sesión, orden, línea, pago, método de pago y pagos manuales/maestros personalizados.
- Ventas: pedido y líneas por `warehouse_id`.
- Inventario: tipos de operación, ubicaciones, quants, pickings, movimientos y líneas. El almacén del tipo de operación es la autoridad; si no existe tipo/picking, solo se permite operar desde una ubicación origen del almacén autorizado. Un destino autorizado por sí solo no concede acceso al stock de otra sucursal.
- Transferencias: conserva los grupos y reglas de `ferreteria_pos_transfer_request_ferre`; permite leer el catálogo de almacenes para elegir contraparte y limita los documentos operativos por ubicación/almacén.
- Ventas solo consulta: grupo reutilizable que da visibilidad a todos los pedidos de la compañía y una regla global que deniega cualquier escritura.

## Promoción

No instalar en producción sin checkpoint verificado, revisión de código y UAT aprobada. Copiar el directorio a un `custom_addons_ferreteria` separado, incluir esa ruta antes de los addons estándar, actualizar la lista de aplicaciones, instalar el módulo y asignar ámbitos usuario por usuario. Mantener `ferreteria_scope_enforced=False` hasta que cada asignación haya sido revisada.
