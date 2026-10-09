# Changelog

## 18.0.1.0.2

- Evita que la precisión monetaria de GTQ reduzca el precio unitario visual a dos decimales durante el cálculo fiscal.
- Aplica `Product Price` (6 decimales) exclusivamente al precio unitario mostrado.
- Conserva sin cambios el cálculo estándar de impuestos y totales de línea de Odoo.

## 18.0.1.0.1

- Usa el resultado fiscal crudo de Odoo antes del redondeo monetario para mostrar el precio unitario con hasta seis decimales.
- Mantiene el total de línea estándar de Odoo, con el redondeo de moneda vigente.
- Elimina ceros decimales innecesarios de la cantidad y muestra `Unidad` cuando la cantidad es uno.

## 18.0.1.0.0

- Presenta el precio unitario del POS con hasta seis decimales.
- Presenta cantidad, UDM, precio unitario y total estándar de línea en una fila compacta.
- Conserva la indicación de descuento cuando corresponde.
- Limita el cambio visual al resumen de venta; no altera el recibo térmico ni cálculos del POS.
