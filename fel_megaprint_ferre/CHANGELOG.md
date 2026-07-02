# Changelog

## 18.0.1.2.1

- Stores the final certified XML returned by Megaprint in `documento_xml_fel`.
- The XML attached by the safe posting module now contains `NumeroAutorizacion`, series and DTE number.
- Adds **Recuperar XML certificado FEL** for already certified invoices; it never recertifies.
- Validates that a recovered XML belongs to the invoice UUID before storing it.
- Removes residual `.bak` and `OLD` Python files from the delivery ZIP.
