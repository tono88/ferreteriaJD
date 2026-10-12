# Validación obligatoria — COPIA_PRDO_CUIDADO — 18.0.2.3.3

**Ambiente único autorizado para homologación:** COPIA_PRDO_CUIDADO.
**Módulo de referencia INALTERADO:** ferreteria_user_scope_ferre 18.0.1.2.0 (13/13 PASS previos).
**No ejecutar en producción.** Antes de probar, respaldar la copia y anotar balances de los productos elegidos. Usar productos almacenables de prueba y cantidades pequeñas.

La creación técnica de documentos debe dispararse **exclusivamente** por `action_approve_all` o `action_approve_partial` y con la sesión real del encargado correspondiente. No crear pickings manuales para imitar la solicitud.

| # | Caso | Procedimiento y criterio PASS | Resultado UAT |
| - | - | - | - |
| 1 | Aprobación total | Con Yumari, aprobar solicitud nueva **Taxisco solicita a Palinche**. Estado `approved`, aprobación atribuida a Yumari, sin `AccessError`. | PENDIENTE |
| 2 | Parcial | Solicitar 8 de producto con stock suficiente; aprobar 5. Ambos `stock.move.product_uom_qty = 5`, solicitud `partial`, 3 no se reservan, origen ligado a destino. | PENDIENTE |
| 3 | Rechazo | Sobre solicitud nueva `submitted`, establecer motivo y rechazar; estado `rejected`, cero pickings y movimientos derivados. | PENDIENTE |
| 4 | Segunda combinación | Una tercera sucursal solicita a otra proveedora; aprobar con encargado autorizado de la proveedora. Mismos criterios del caso 1. | PENDIENTE |
| 5 | Usuario ajeno | Usuario con aprobación solo de tercera sucursal intenta aprobar solicitud cuyo proveedor es Palinche; `AccessError` sin crear nada. | PENDIENTE |
| 6 | Acceso directo | Con Yumari intentar crear/validar manualmente una transferencia con el tipo `Taxisco: Traslados internos` sin solicitud. Debe bloquearse la **operación**. Nota: el tipo de operación puede ser **legible** por diseño (regla 318 `perm_read=False`), lo que NO concede permiso para operar. | PENDIENTE |
| 7 | Pickings | Verificar `Palinche/Existencias -> Tránsito` (tipo interno Palinche) y `Tránsito -> Taxisco/Existencias` (tipo interno Taxisco). IDs de solicitud/etapa y vínculos por línea correctos. Recepción `procure_method=make_to_order`, origen = movimiento despacho. | PENDIENTE |
| 8 | Inventario | Tras aprobar: sin traslado físico (solo reserva); tras despachar: baja proveedor y sube tránsito; tras recibir: baja tránsito y sube destino. La suma de unidades físicas permanece constante; sin dobles existencias. | PENDIENTE |
| 9 | Atomicidad | En copia aislada forzar excepción al preparar/crear la recepción o después de asignar la reserva; `action_approve_all` debe abortar y dejar solicitud `submitted`, cero pickings/moves huérfanos, cero reserva adicional. Hay pruebas Odoo en `tests/test_transfer_request.py` para ambas inyecciones, ejecutables con `--test-enable`. | PENDIENTE |
| 10 | Scopes | Repetir operación manual sobre almacén ajeno con usuario scoped y comprobar bloqueo; lectura global de inventario y POS especial no se alteran; repetir la suite de 13 casos de scopes. | PENDIENTE |

## Ejecución controlada

1. Verificar que el módulo instalado **ferreteria_user_scope_ferre** se mantiene en `18.0.1.2.0` y que NO se actualizará durante esta fase.
2. Copiar el nuevo ZIP al addons_path de la copia, respaldar DB, reiniciar solo la instancia de la copia y actualizar **exclusivamente** `ferreteria_pos_transfer_request_ferre` a `18.0.2.3.3`.
3. No modificar XML/reglas de seguridad, usuarios, almacenes, tipos de operación ni permisos POS. Guardar capturas/logs y anotar los ID de nuevas solicitudes.
4. Ejecutar casos 1–10. El caso 9 debe correrse solo en la copia y, preferiblemente, con las pruebas automatizadas de Odoo activadas; no activar un fallo artificial en producción.
5. Documentar `PASS/FAIL`, referencia STS, usuario, origen/destino y evidencia de cada caso antes de aceptar.

**Importante:** El `sudo()` técnico se limita a crear el picking y los movimientos de recepción, y a confirmar/reservar exclusivamente los movimientos derivados de la solicitud; la autorización de la solicitud y todos sus cambios de estado conservan al usuario real.
