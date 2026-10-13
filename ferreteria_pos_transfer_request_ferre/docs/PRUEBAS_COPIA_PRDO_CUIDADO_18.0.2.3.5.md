# Homologación 18.0.2.3.5 — STS/2026/00038 Mayoreo → Taxisco

**ÚNICA BASE DE PRUEBAS:** `COPIA_PRDO_CUIDADO`. **PRODUCCIÓN PROHIBIDA.**

## Fuente y alcance

- ZIP base exacto: `ferreteria_pos_transfer_request_ferre_18.0.2.3.4.zip`.
- SHA-256 base verificado: `678f8de2387bdf9fb3d02b7ea1648c13e88d95ea289418099f7007dd466d0bb2`.
- Módulo destino: `ferreteria_pos_transfer_request_ferre` versión `18.0.2.3.5`.
- Referencia INALTERADA: `ferreteria_user_scope_ferre 18.0.1.2.0` (13/13 pruebas previamente PASS).
- Incidente: `STS/2026/00038`, solicitante Mayoreo, proveedor Taxisco, aprobadora Ingrid de Paz `res.users(13)`, POS solicitante `pos.config(8)`.
- Restricción original: regla **Ferretería: POS permitidos** impide leer POS Mayoreo con Ingrid; mantenerla.

## Diagnóstico del código exacto 18.0.2.3.4

1. `action_approve_all()` → `_action_approve()` → `_ensure_approver_access()` confirma al usuario real en el almacén **suministrador** (Taxisco).
2. `_create_and_reserve_pickings()` vuelve a validar la autorización y llama a `_check_branch_configuration()`.
3. `_check_branch_configuration()` consulta `requesting_pos_id._ferreteria_transfer_warehouse()`; en `models/pos_config.py` lee `pos.config.picking_type_id.warehouse_id` y, si falta, `pos.config.warehouse_id`.
4. Como Ingrid no puede leer el POS Mayoreo, se genera `AccessError` antes de crear los dos pickings. La elevación anterior para el picking y los moves de recepción **no cubría esa lectura**.

## Cambios exclusivos en 18.0.2.3.5

- `_check_branch_configuration(technical_pos_read=False)` conserva por defecto todas las lecturas con el usuario real para `@api.constrains`, creación y edición; **no cambia los permisos globales**.
- Solo `_create_and_reserve_pickings()` pasa `technical_pos_read=True`, después de autorizar al usuario real, verificar estado, líneas, cantidades y ausencia de pickings existentes.
- La verificación de compañía y sucursales continúa con el usuario real; antes de `pos_config.sudo()` se repite `_ensure_approver_access()` como defensa en profundidad.
- El `sudo()` solo toca el **registro concreto** de `requesting_pos_id` para obtener su almacén; no expone una búsqueda de POS ni otorga acceso a menús u operaciones ajenas.
- No se tocó `skip_backorder=True` ni la lógica de aprobación parcial, despacho, recepción, incidencias, stock o atomicidad.

## Preparación de UAT

1. Confirmar aislamiento DB/runtime/filestore/addons de `COPIA_PRDO_CUIDADO` y neutralización de FEL, SMTP, webhooks y crons de producción. No reutilizar rutas de addons compartidas con producción.
2. Hacer dump restaurable de PostgreSQL, copia del filestore y backup del módulo `18.0.2.3.4`. Registrar SHA-256 de cada copia.
3. Verificar que `ferreteria_user_scope_ferre` siga instalado en `18.0.1.2.0`; registrar reglas de POS y stock antes/después.
4. Actualizar **solo** `ferreteria_pos_transfer_request_ferre` usando la configuración aislada de UAT. Verificar `ir.module.module.latest_version`, manifest y ruta efectiva.
5. Ejecutar Odoo tests post_install con `--test-enable --test-tags /ferreteria_pos_transfer_request_ferre` sobre la **copia**. `@tagged('post_install', '-at_install')` requiere un ciclo de carga/actualización que ejecute post_install. Verificar logs, no asumir que los tests se ejecutaron.
6. No crear ni modificar pickings, inventario o datos reales fuera de la copia. Si `STS/2026/00038` ya no está pendiente en la copia, preservar su estado y reproducirlo con solicitud nueva equivalente en UAT; no forzar cambios históricos.

## Matriz funcional — 11 casos obligatorios

| # | Caso | PASS requiere | UAT |
|---|---|---|---|
| 1 | **STS/2026/00038**, Mayoreo → Taxisco, Ingrid (13) → Aprobar todo | Si está pendiente, estado `approved`, sin `AccessError`; si no, reproducir en nueva solicitud y registrar referencia; `approved_by_id=13` | PENDIENTE |
| 2 | Ingrid sin acceso al POS Mayoreo | `pos.config(8).read(...)`/menú/operaciones siguen denegados por regla; POS autorizados intactos | PENDIENTE |
| 3 | Aprobación parcial Mayoreo → Taxisco | Solicitar 8, aprobar 5; estado `partial`, despacho y recepción 5, restante no reservado | PENDIENTE |
| 4 | Rechazo Mayoreo → Taxisco | Estado `rejected`, cero pickings y moves nuevos | PENDIENTE |
| 5 | Otra combinación de sucursales | Aprobador autorizado, sucursales correctas, dos pickings coherentes | PENDIENTE |
| 6 | Tercera sucursal no autorizada | `AccessError` **antes** de cualquier lectura técnica `sudo` y antes de crear pickings | PENDIENTE |
| 7 | Despacho correcto | `Taxisco/Existencias → Tránsito`, tipo interno Taxisco, trazabilidad origen y líneas | PENDIENTE |
| 8 | Recepción correcta | `Tránsito → Mayoreo/Existencias`, tipo interno Mayoreo, `move_orig_ids` despacho→recepción | PENDIENTE |
| 9 | Inventario | Al aprobar solo reserva; al despachar/recibir conservación de cantidad y cero duplicación en tránsito | PENDIENTE |
| 10 | Atomicidad | Inyectar fallo al crear recepción y tras reservar en test: estado, moves, quants y picking links vuelven a estado previo | PENDIENTE |
| 11 | Acceso directo de Ingrid a `pos.config(8)` | Denegado fuera de la aprobación por la regla real, incluyendo intento RPC de lectura | PENDIENTE |

**Regresiones complementarias:** 13/13 casos de `ferreteria_user_scope_ferre` y recepción corta (`skip_backorder=True` sin backorder huérfano) deben conservar PASS.

## Evidencias obligatorias

Para cada caso: usuario real, IDs, referencia STS, operaciones y ubicaciones, estado antes/después, movimientos y cantidades, existencia física/reservada, resultado (`PASS`, `FAIL`, `NO EJECUTADA`), traceback si aplica. No declarar PASS por pruebas estáticas. **No promover a producción.**
