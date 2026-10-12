# Changelog

## 18.0.1.5.2 — Corrección candidata de pagos globales, 2026-10-12

- Mantiene el selector global por grupo y el Many2one original para usuarios operativos scoped.
- Corrige la pérdida de pagos de otras sucursales en PDF y XLSX para lectores globales; los pagos se consultan mediante `pos.payment.sudo()` exclusivamente para los IDs de órdenes obtenidos con permisos normales y compañías autorizadas.
- Se conserva `pos.order.search()` sin `sudo()` y se mantienen filtros, reembolsos, correlativos, reportes y totales.
- Usuarios sin el grupo global continúan usando `order.payment_ids` sin elevación.
- No modifica reglas de acceso, usuarios, `ferreteria_user_scope_ferre` ni configuraciones operativas.
- Candidato NO VALIDADO en `COPIA_PRDO_CUIDADO`: antes de aprobar, reproducir con el script de auditoría y cotejar pagos/órdenes de Taxisco y Palinche en PDF y XLSX.

## 18.0.1.5.1 — Hotfix de selector por grupo, 2026-10-12

- Corrige la visibilidad del filtro POS directamente por grupo en la vista (atributo `groups`), evitando depender del booleano calculado `can_select_global_pos` para mostrar el selector.
- Usuarios con `ferreteria_user_scope_ferre.group_pos_global_order_read`: ven `global_pos_config_id` (catálogo de reporte); usuarios restantes: ven `pos_config_id` (Many2one original, scope intacto).
- Declara dependencia explícita de `ferreteria_user_scope_ferre`, ya instalado en el entorno objetivo, para asegurar la resolución del grupo al actualizar vistas.
- No cambia los métodos Python, filtros, PDF/XLSX, reglas de acceso, POS operativos ni cálculos de pagos. No requiere actualizar el módulo de scopes.
- Requiere actualizar el módulo, no basta copiar el ZIP: comparar vista XML persistida y permisos reales. Probar exclusivamente en `COPIA_PRDO_CUIDADO`.
- `pos.payment` sigue pendiente de reproducción funcional con órdenes reales.

## 18.0.1.5.0 — 2026-10-11

- Añade un selector técnico **solo de reporte** para usuarios con `group_pos_global_order_read`.
- Lista exclusivamente los POS activos de las compañías autorizadas, sin ampliar permisos de `pos.config` ni el scope operativo.
- Conserva el selector `pos_config_id` original para usuarios normales.
- Valida el POS elegido en servidor tanto en el wizard como al buscar las órdenes del reporte, incluso frente a datos RPC manipulados.
- Mantiene sin cambios la consulta ordinaria de `pos.order`, la separación de pagos, filtros, reembolsos, PDF y XLSX.
- **Pendiente en COPIA_PRDO_CUIDADO:** reproducción del posible efecto de `rule_pos_payment_scope` sobre totales intersucursal; no se modifican pagos sin evidencia funcional.

## 18.0.1.4.0 — 2026-07-20

- Añade la columna `Fecha documento` en PDF y XLSX.
- Usa `account.move.invoice_date` para facturas publicadas.
- Usa `pos.order.date_order` en zona horaria local para comprobantes e inconsistencias.
- Añade observaciones para facturas canceladas, en borrador, sin fecha o sin vínculo.
- Corrige el orden numérico de correlativos con prefijos.
- Aplica los filtros de cliente y POS también al análisis de reembolsos.
- Cambia el PDF a orientación horizontal para conservar legibilidad.
