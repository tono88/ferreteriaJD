Ferretería - Boleta en listado y buscador de pagos
================================================
Compatible con Odoo 18.0.

REQUISITO
Debe estar instalado ferreteria_bank_slip_unique_ferre y sus dependencias.
Se reutiliza el campo account.payment.bank_reference existente.

INSTALACIÓN
1. Activa el modo desarrollador en Odoo.
2. En Aplicaciones, abre Importar módulo.
3. Selecciona ferreteria_bank_reference_search_ferre.zip sin descomprimir.
4. Importa y vuelve a abrir Facturación > Clientes > Pagos.

USO
La columna "No. boleta bancaria" aparece después de "Número".
Si no aparece por una preferencia guardada, actívala en el selector de columnas.
En el buscador escribe la boleta y selecciona "No. boleta bancaria".
La búsqueda admite el número completo o una parte.
Los pagos sin referencia muestran la celda vacía.
Las vistas compartidas pueden mostrar también la columna en pagos de proveedores.

ALCANCE
Solo agrega dos vistas heredadas. No crea campos ni modifica pagos.
No cambia la validación de boletas únicas del módulo original.
No requiere reiniciar el servidor ni agregar código Python ejecutable.
Para revertir, desinstala este complemento.

VALIDACIÓN
Se verificó la estructura XML, los identificadores de las vistas y los
puntos de inserción contra el código oficial de Odoo 18.0.
Se confirmó en tono88/ferreteriaJD que bank_reference es un campo Char
en account.payment y que el módulo original es versión 18.0.
No se ejecutó una instalación en una base de datos Odoo.

REFERENCIAS
https://github.com/tono88/ferreteriaJD/tree/main/ferreteria_bank_slip_unique_ferre
https://github.com/odoo/odoo/blob/18.0/addons/account/views/account_payment_view.xml
https://www.odoo.com/documentation/18.0/developer/tutorials/importable_modules.html