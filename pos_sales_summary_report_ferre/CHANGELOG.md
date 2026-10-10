# Changelog

## 18.0.1.5.0 — 2026-10-10

- Corrige el reporte de un solo día: el inicio y el final se interpretan
  usando la **zona horaria de la compañía**, no la de cada usuario.
  Si la compañía no tiene una zona configurada, usa America/Guatemala.
- La conversión a UTC emplea el inicio del día siguiente como límite
  exclusivo (incluye ventas hasta las 23:59:59 con fracciones de segundo).
- Añade opción **Filtrar por** (predeterminada: Fecha del documento):
  - **Fecha del documento**: para factura publicada se utiliza
    `account.move.invoice_date` (fecha fiscal); para operaciones sin
    factura publicada se usa `pos.order.date_order` en zona local.
  - **Fecha de la operación POS**: se conservan los filtros anteriores
    basados en `pos.order.date_order`, con la zona comercial corregida.
- PDF y XLSX utilizan el mismo filtro y muestran la zona y el criterio.
- Mantiene filtros de POS, clientes, facturadas y correlativo interno.
- Añade pruebas de regresión: factura del 7 vs. venta POS del 8,
  límites UTC del 8/10 en Guatemala y zonas con horario de verano.

### Verificación operativa

1. En *Ajustes → Compañías* revisar que el contacto de la empresa tenga
   zona horaria `America/Guatemala` (dejar sin zona también utiliza GT).
2. Actualizar el módulo y abrir **Reporte de ventas (POS)**.
3. Seleccionar Desde = Hasta = 08/10/2026 y **Filtrar por = Fecha del
   documento**. Ana Lucía y otro usuario deben obtener el mismo conjunto
   de documentos y totales, si ambos tienen acceso a las mismas operaciones.
4. Un comprobante cuya factura publicada tenga `invoice_date=07/10/2026`
   NO debe aparecer en el día 8, aunque su `pos.order.date_order` caiga el 8.
5. Cambiar a **Fecha de la operación POS** para consultar operaciones
   realizadas el 8 sin importar la fecha fiscal de la factura.
6. Comparar PDF y XLSX, reembolsos, filtros y totales.

**Nota:** se modifica cómo se determinan los documentos que pertenecen a
cada día. No se alteran facturas, fechas contables, asientos ni existencias.

## 18.0.1.4.0 — 2026-07-20

- Añade la columna `Fecha documento` en PDF y XLSX.
- Usa `account.move.invoice_date` para facturas publicadas.
- Usa `pos.order.date_order` en zona horaria local para comprobantes e inconsistencias.
- Añade observaciones para facturas canceladas, en borrador, sin fecha o sin vínculo.
- Corrige el orden numérico de correlativos con prefijos.
- Aplica los filtros de cliente y POS también al análisis de reembolsos.
- Cambia el PDF a orientación horizontal para conservar legibilidad.
