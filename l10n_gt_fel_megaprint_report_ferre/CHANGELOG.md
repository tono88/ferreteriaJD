# Changelog

## 18.0.1.0.2

- Sustituye la marca comercial fija de otra empresa por el nombre comercial configurado en `journal_id.direccion.name`.
- Mantiene como respaldo el nombre legal de la compañía.
- Elimina del paquete el archivo residual `report_fel_invoice.xml.bak`.
- Conserva las referencias QWeb bajo el namespace técnico `_ferre`.


## 18.0.1.0.1

- Removed the obsolete dependency on `pos.order.line.stock_location_name`.
- Resolves the warehouse from the POS configuration/picking type.
- Adds a sales-order warehouse fallback.
- Missing warehouse information no longer interrupts FEL PDF rendering.

## 18.0.1.0.3

- Removes fixed fiscal legends from the PDF.
- Prints only the FEL phrases embedded in the invoice XML, with company configuration as fallback.
- Historical reprints no longer inherit a phrase added later to the company.
- The IVA withholding-agent legend is not printed unless phrase type 2, scenario 1 is actually present.
