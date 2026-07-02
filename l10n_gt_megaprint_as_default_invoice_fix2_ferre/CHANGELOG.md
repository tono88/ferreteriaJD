# Changelog

## 18.0.1.3.0

- Corrige acciones de reporte que todavía apuntan al namespace anterior `l10n_gt_fel_megaprint_report.report_fel_invoice`.
- Sincroniza el reporte predeterminado con `l10n_gt_fel_megaprint_report_ferre.report_fel_invoice` durante instalación y actualización.
- Realiza la corrección mediante ORM y sin SQL.
- No crea, modifica ni certifica facturas.
- Agrega logging seguro con la marca `[FEL_REPORT_SYNC]`.
