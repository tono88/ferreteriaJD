# Cotizaciones desde el punto de venta — Ferretería JD (Odoo 18)

Módulo **implementado de forma independiente** para permitir cotizaciones en
POS sin publicar el código del módulo comercial de referencia, cuya licencia
OPL-1 prohíbe redistribuir el paquete original en un repositorio público.

- Botón **Crear cotización** en las opciones del carrito POS.
- Conserva cliente, artículos, cantidades, precios y descuentos.
- Impuestos calculados por Odoo según cliente, producto y posición fiscal.
- Tras crear: mantener cotización en borrador o confirmar como pedido.
- En el selector de pedidos del POS: **Visualizar (PDF)**, **Enviar por correo**
  (plantilla estándar con PDF adjunto), **Imprimir (PDF)**, **Confirmar**,
  **Cancelar** y **Cobrar / anticipo** (flujo original de `pos_sale`).
- La impresión se realiza mediante la acción PDF estándar de Odoo; la
  impresión directa en impresora térmica requeriría una integración adicional.

**Instalación:** Odoo 18 con `point_of_sale`, `pos_sale`, `sale_management`
y `mail`. Active «Permitir crear cotizaciones desde el POS» en ajustes del POS.
Los operadores deben tener permisos adecuados sobre ventas/cotizaciones.

**Correo:** requiere dirección de correo en el cliente y servidor saliente
configurado en Odoo. El usuario confirma el envío antes de realizarlo.
