# Changelog

## 18.0.2.0.1 — 2026-09-30

- Sustituye en el recibo térmico POS las líneas básicas de Odoo por líneas compactas propias del ticket.
- Muestra siempre `cantidad + unidad × precio unitario` y el subtotal de cada línea.
- Mantiene el descuento visible únicamente cuando es mayor que cero.
- Alinea el PDF backend con la misma presentación compacta usada en pantalla, impresión y reimpresión POS.

## 18.0.2.0.0 — 2026-09-30

- Unifica el ticket térmico de 80 mm para ventas con FEL y sin FEL.
- Separa visualmente Serie interna / No. interno de Serie DTE / Número DTE.
- Añade nombre, dirección y teléfono configurables por POS.
- Añade estado PAGADO/PENDIENTE DE PAGO y evita inferir anulación FEL desde una cancelación local.
- Mantiene literalmente las tres leyendas comerciales/fiscales confirmadas por JB.
- Carga los datos del servidor antes de impresión automática y antes de reimpresión.
- Conserva correlativo, DTE, autorización e importes al reimprimir.
- Fuerza UTF-8 solo en el PDF térmico para evitar texto corrupto en wkhtmltopdf sobre Windows.

## 18.0.1.0.2 — 2026-07-21

- Muestra `No. interno` en el recibo POS de ventas sin factura FEL.
- Reutiliza el correlativo obtenido desde `get_fel_ticket_data_for_pos`.
- No modifica `PosOrder`, la creación de órdenes, clientes, pagos, líneas, listas de precios ni IndexedDB.
- Conserva sin cambios la presentación del recibo FEL facturado.

## 18.0.1.0.1 — 2026-07-20

- Añade `No. interno` al recibo POS FEL.
- Añade `No. interno` al ticket térmico PDF del backend.
- Mantiene el dato visible también en comprobantes sin factura FEL.
- Declara dependencia explícita de `pos_internal_correlative_ferre`.
