# QA / homologación — 18.0.1.2.0

**Ambiente ÚNICO permitido:** `COPIA_PRDO_CUIDADO`. No instalar en `FERRE_PROD` ni en producción publicada.

## Preparación

1. Resguardar copia de base y filestore; registrar ruta de addons y módulos instalados. Anotar los XML-ID de reglas 318–322 (los IDs SQL pueden variar entre bases).
2. Antes de actualizar capturar `domain_force`, `perm_read`, `perm_write`, `perm_create`, `perm_unlink` y `active` de las cinco reglas.
3. En la copia y solo allí: colocar esta versión en `addons_path`, actualizar `ferreteria_user_scope_ferre`; revisar log de carga XML (sin errores).
4. Confirmar dominios 321/322 con igualdad literal contra este paquete y que 318/319/320 tengan read=False y otras operaciones=True.
5. Confirmar que Ana Lucía conserva `ferreteria_scope_enforced=True`, únicamente JBC en `ferreteria_allowed_pos_ids` y JBC en almacenes; asignarle el grupo **Lectura global de órdenes POS**. No asignar `Punto de Venta: solo consulta`.
6. Comprobar pertenencia y acceso por compañías; efectuar pruebas como cada usuario sin `sudo`.

## Matriz funcional (marcar tras ejecutarse en Odoo)

| # | Usuario / escenario | Resultado esperado | Estado |
|---|---|---|---|
| 1 | Encargado JBC consulta existencias de otras sucursales | Lectura permitida | Pendiente UAT |
| 2 | Encargado JBC crea y valida operación sobre JBC | Permitido | Pendiente UAT |
| 3 | Encargado JBC intenta modificar inventario de otra sucursal | Denegado | Pendiente UAT |
| 4 | Encargado aprueba solicitud intersucursal autorizada | Permitido; rollback | Pendiente UAT |
| 5 | Encargado intenta aprobar solicitud NO autorizada | Denegado; rollback | Pendiente UAT |
| 6 | Ana Lucía abre, vende y cierra sesión en JBC | Permitido; rollback | Pendiente UAT |
| 7 | Ana Lucía intenta abrir otro POS desde UI y por RPC | Denegado | Pendiente UAT |
| 8 | Ana Lucía consulta órdenes de otros POS en backend | Lectura permitida | Pendiente UAT |
| 9 | Ana Lucía consulta líneas/detalle de órdenes ajenas | Lectura permitida | Pendiente UAT |
| 10 | Ana Lucía consulta reporte de sesión, ventas y análisis POS | Histórico global; documentar cualquier bloqueo por otros modelos | Pendiente UAT |
| 11 | Ana Lucía intenta escribir/borrar una orden ajena vía ORM/RPC | Denegado | Pendiente UAT |
| 12 | Usuario scoped normal (sin grupo nuevo) consulta órdenes de otros POS | Denegado | Pendiente UAT |
| 13 | Usuario `Punto de Venta: solo consulta` intenta crear venta/abrir POS | Denegado | Pendiente UAT |

## Precauciones

- **No** registrar ventas, movimientos ni aprobaciones con persistencia en una base que vaya a reutilizarse. Ejecutar en transacción que haga rollback o restaurar snapshot/fixture luego de las pruebas.
- Comprobar que los reportes propios no impongan dominios adicionales en acciones, vistas, JS, controladores u otros módulos.
- `pos.config`, `pos.session` y `pos.payment` siguen restringidos. Si un reporte falla por lectura de un modelo relacionado, documentar el modelo y regla exactos antes de una ampliación selectiva.
- Las reglas `ir.rule` no reemplazan la revisión de métodos `sudo()` o controladores que pudieran omitir ACL; probar las operaciones sensibles por RPC sin superusuario.
- Si falla cualquiera de las 13 pruebas, **NO PROMOVER** la versión a producción.
