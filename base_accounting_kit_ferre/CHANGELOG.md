# Changelog

## 18.0.4.0.7 — 2026-08-05

### Fixed

- Corrected the `model_id` used by the access rule for the financial report QWeb model.
- Replaced the obsolete external identifier `model_report_base_accounting_kit_report_financial` with `model_report_base_accounting_kit_ferre_report_financial`, matching the renamed model `report.base_accounting_kit_ferre.report_financial`.
- This resolves the clean-database installation error raised while loading `security/ir.model.access.csv`.

### Maintenance

- Removed compiled Python cache artifacts from the deliverable.
- No accounting behavior, reports, menus, permissions, or business data were otherwise changed.
