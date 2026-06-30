# Riesgos y limitaciones conocidas

1. **Prueba visual del POS pendiente en la instancia del usuario.** El backend de la Fase 1 ya fue validado manualmente en la base del usuario. Los assets OWL de esta versión se validaron estáticamente, pero deben probarse en el navegador y compilación de assets de esa instalación concreta.
2. **Caché de assets.** Después de actualizar es obligatorio cerrar el POS y hacer una recarga completa. Mantener abierta una pestaña anterior puede ocultar el nuevo botón o ejecutar JavaScript obsoleto.
3. **Productos solicitables.** Solo aparecen productos activos con `is_storable=True`. Servicios y bienes sin seguimiento de inventario quedan excluidos porque no pueden producir una transferencia física útil.
4. **Existencia informativa.** El valor mostrado en POS puede cambiar por otras operaciones concurrentes. La aprobación vuelve a reservar y validar toda la cantidad en el servidor.
5. **Conectividad.** La creación desde POS requiere conexión con el servidor. No se almacena una solicitud offline ni se sincroniza posteriormente.
6. **Productos con seguimiento.** Los lotes y series se completan en las operaciones detalladas estándar antes del despacho o recepción; no se solicitan desde el diálogo inicial.
7. **Diferencias permanecen en tránsito.** Cuando se recibe menos de lo despachado, el saldo físico queda en tránsito hasta definir devolución, ajuste, merma o pérdida.
8. **Sin impacto contable de incidencias.** Las incidencias son documentales; no crean asientos ni ajustes.
9. **Ubicaciones principales.** El flujo usa `lot_stock_id` y el tipo de operación interna de cada almacén. No interpreta rutas avanzadas o sububicaciones específicas.
10. **Permisos estándar de Inventario.** Los grupos del módulo implican usuario de Inventario para operar los pickings backend; la política general de acceso a Inventario debe revisarse antes de producción.
11. **Totales con UDM heterogéneas.** Los totales de encabezado son sumas operativas; la fuente exacta son las cantidades por línea.
12. **Una sola compañía.** No se permiten transferencias intercompañía.
13. **Compatibilidad con otros módulos POS.** Otros módulos que reemplacen el mismo componente OWL sin usar extensiones compatibles pueden requerir una revisión conjunta de assets.
