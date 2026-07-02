# Ferretería - Ticket FEL para Punto de Venta (Odoo 18)

Módulo enfocado únicamente en impresión:

1. Convierte el recibo final del Punto de Venta en un ticket con datos de la factura FEL vinculada.
2. Agrega **Imprimir → Ticket FEL térmico** en las órdenes POS del backend.

No crea facturas, no certifica, no modifica cierres de sesión, no altera devoluciones y no cambia líneas de factura.

## Compatibilidad FEL

La integración vigente del proyecto utiliza estos campos en `account.move`:

- `firma_fel`
- `serie_fel`
- `numero_fel`
- `documento_xml_fel`

El módulo prioriza el XML certificado y esos campos. También reconoce variantes comunes de nombres para no duplicar la lógica del módulo Megaprint.

## Instalación

1. Copiar la carpeta `ferreteria_pos_fel_ticket` al `addons_path`.
2. Reiniciar Odoo.
3. Actualizar la lista de aplicaciones.
4. Instalar **Ferretería - Ticket FEL para Punto de Venta**.
5. Cerrar y volver a abrir la sesión POS; después hacer una recarga forzada del navegador (`Ctrl + F5`).

## Uso

- En el POS, facture la venta y finalícela. La pantalla de recibo consulta la factura vinculada y muestra serie, número, autorización, fechas, emisor, receptor y certificador.
- En backend: **Punto de venta → Pedidos → Pedidos**, abra o seleccione una orden y use **Imprimir → Ticket FEL térmico**.

## Papel

El PDF usa papel de 80 mm de ancho. El formato no se marca como predeterminado, por lo que no modifica otros reportes de Odoo.
