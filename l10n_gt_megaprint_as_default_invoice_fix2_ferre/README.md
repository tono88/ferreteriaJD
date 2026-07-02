# GT Megaprint como factura por defecto — FERRE

Este módulo configura el reporte FEL `_ferre` como PDF predeterminado de las facturas.
También repara referencias antiguas que apunten a `l10n_gt_fel_megaprint_report.report_fel_invoice`.

## Actualización

1. Actualizar primero `l10n_gt_fel_megaprint_report_ferre`.
2. Actualizar este módulo.
3. Confirmar en el log la línea `[FEL_REPORT_SYNC]`.

La sincronización usa ORM y no vuelve a certificar documentos.
