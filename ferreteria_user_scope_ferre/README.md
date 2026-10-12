# Ferretería - Seguridad por POS y almacén

Módulo de Odoo 18 para activar, por usuario y de forma explícita, un ámbito operativo de POS y almacenes.

## Campos de usuario

- `ferreteria_scope_enforced`: activa las reglas globales de servidor.
- `ferreteria_allowed_pos_ids`: POS autorizados.
- `ferreteria_allowed_warehouse_ids`: almacenes autorizados.
- `ferreteria_sales_readonly`: bloquea crear, editar y eliminar pedidos y líneas de venta.
- Grupo `group_pos_global_order_read` (`Lectura global de órdenes POS`): permite leer órdenes y líneas POS de las compañías autorizadas, sin quitar scope ni ampliar permisos operativos. Se asigna mediante los grupos del usuario y **no** implica `Punto de Venta: solo consulta`.

La validación exige al menos un almacén cuando el ámbito está activo y comprueba que los POS asignados pertenezcan a los almacenes permitidos. Los usuarios sin ámbito conservan el comportamiento estándar; el superusuario conserva el bypass nativo de reglas.

## Cobertura

- POS: configuración, sesión, orden, línea, pago, método de pago y pagos manuales/maestros personalizados.
- Ventas: pedido y líneas por `warehouse_id`.
- Inventario: tipos de operación, ubicaciones, quants, pickings, movimientos y líneas. El almacén del tipo de operación es la autoridad; si no existe tipo/picking, solo se permite operar desde una ubicación origen del almacén autorizado. Un destino autorizado por sí solo no concede acceso al stock de otra sucursal.
- Transferencias: conserva los grupos y reglas de `ferreteria_pos_transfer_request_ferre`; permite leer el catálogo de almacenes para elegir contraparte y limita los documentos operativos por ubicación/almacén.
- Ventas solo consulta: grupo reutilizable que da visibilidad a todos los pedidos de la compañía y una regla global que deniega cualquier escritura.

## Promoción

No instalar en producción sin checkpoint verificado, revisión de código y UAT aprobada. Copiar el directorio a un `custom_addons_ferreteria` separado, incluir esa ruta antes de los addons estándar, actualizar la lista de aplicaciones, instalar el módulo y asignar ámbitos usuario por usuario. Mantener `ferreteria_scope_enforced=False` hasta que cada asignación haya sido revisada.

## Versión 18.0.1.2.0 — cambios consolidados (NO promover sin UAT)

- Inventario: `rule_stock_picking_type_scope` (318), `rule_stock_location_scope` (319) y `rule_stock_quant_scope` (320) declaran `perm_read=False`; sus dominios de operación son iguales a 18.0.1.1.0; write/create/unlink=True.
- Solicitudes: `rule_stock_picking_scope` (321) y `rule_stock_move_scope` (322) incluyen **literalmente** los dominios recibidos de `COPIA_PRDO_CUIDADO`, preservando el workaround temporal. La solución definitiva del flujo de solicitudes pertenece a `ferreteria_pos_transfer_request_ferre`.
- POS: reglas existentes `rule_pos_order_scope` y `rule_pos_order_line_scope` conservan sus IDs y dominios para create/write/unlink y dejan de participar en read; nuevas reglas globales de **solo lectura** mantienen scope normal y permiten lectura entre POS a usuarios con `group_pos_global_order_read`, limitada a compañías permitidas activas.
- `pos.config`, `pos.session`, `pos.payment` y demás reglas: sin modificaciones.
- `group_pos_readonly` y sus defensas de servidor: sin cambios.
- El grupo nuevo no se asigna automáticamente a ningún usuario. Tras actualizar **COPIA_PRDO_CUIDADO**, asignarlo a Ana Lucía en Ajustes > Usuarios y compañías > Usuarios > Derechos de acceso > Seguridad Ferretería.

**Atención:** el acceso real a los reportes personalizados, vistas relacionadas, pagos y sesiones requiere validación funcional con esa copia y sus addons; esos resultados no pueden inferirse solo del ZIP. Ejecutar la matriz en `docs/PRUEBAS_COPIA_PRDO_CUIDADO.md` y no promover a producción antes de completar la prueba.
