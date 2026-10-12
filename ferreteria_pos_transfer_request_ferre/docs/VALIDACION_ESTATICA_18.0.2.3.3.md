# Validación estática del parche 18.0.2.3.3

**Origen**: ferreteria_pos_transfer_request_ferre 18.0.2.3.2 suministrado por el usuario.
**Referencia intacta**: ferreteria_user_scope_ferre 18.0.1.2.0.

## Resultado ejecutado

- **27/27 comprobaciones estáticas PASS**: manifiesto, dependencias y assets, compilación Python, parseo XML, CSV ACL, orden de validación antes de sudo, ausencia de sudo sobre la acción de aprobación, integridad de dependencias entre movimientos, versión, atomicidad explícita y comparación de archivos originales byte por byte.
- **JavaScript**: comprobación de sintaxis con Node.js sobre ambos archivos POS, sin errores.
- Archivos de código cambiados: `models/transfer_request.py`, `tests/test_transfer_request.py`, `__manifest__.py`; se añadió changelog y documentación de regresión.
- Los demás archivos originales se conservaron byte por byte.
- **Odoo/PostgreSQL no están disponibles en el entorno de empaquetado**. No se ha actualizado `COPIA_PRDO_CUIDADO` ni ejecutado las pruebas de integración Odoo.

## Limitaciones y riesgos pendientes

1. La prueba funcional del `sudo()` en `stock.picking.create` y `stock.move.create` para la sucursal solicitante requiere ORM Odoo 18 con las reglas reales de `COPIA_PRDO_CUIDADO`.
2. La confirmación del despacho y su reserva tienen elevación limitada a los movimientos de este flujo para permitir comprobaciones de dependencias contra la recepción fuera de scope. Validar en la copia que no hay un efecto colateral por rutas/reabastecimiento extra configurado.
3. Se mantiene el workaround en 321/322 durante la fase, por orden expresa. **La independencia conceptual del código NO demuestra por sí misma que pueda retirarse el workaround**. Esto exigiría una homologación posterior en otra fase y con las restricciones autorizadas.
4. La regla 318 permite lectura global de tipos de operación; un usuario scoped puede consultar su nombre pero no operarlos manualmente fuera de sus permisos.
5. El código conserva el despacho técnico con permisos del usuario real; si un aprobador funcional carece además de permisos operativos en el almacén proveedor, la acción puede fallar allí. El escenario aprobado es que el encargado proveedor está scoped en su almacén proveedor.

**Homologación**: PENDIENTE, ver `PRUEBAS_COPIA_PRDO_CUIDADO_18.0.2.3.3.md`. No promover a producción hasta completar 10/10 en esa copia.
