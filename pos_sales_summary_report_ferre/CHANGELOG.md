# Changelog

## 18.0.1.4.0 — 2026-07-20

- Añade la columna `Fecha documento` en PDF y XLSX.
- Usa `account.move.invoice_date` para facturas publicadas.
- Usa `pos.order.date_order` en zona horaria local para comprobantes e inconsistencias.
- Añade observaciones para facturas canceladas, en borrador, sin fecha o sin vínculo.
- Corrige el orden numérico de correlativos con prefijos.
- Aplica los filtros de cliente y POS también al análisis de reembolsos.
- Cambia el PDF a orientación horizontal para conservar legibilidad.
