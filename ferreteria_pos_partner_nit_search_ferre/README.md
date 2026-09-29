# Ferreteria POS Partner NIT Search

Extiende el selector de clientes del Punto de Venta para encontrar un cliente
por coincidencia exacta de NIT aunque el usuario escriba guiones o espacios de
forma diferente. El valor almacenado en `res.partner.vat` no se modifica.

La búsqueda por nombre y el resto de búsquedas estándar permanecen delegadas a
Odoo. La normalización elimina únicamente `-` y espacios.
