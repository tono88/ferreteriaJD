# Corrección cotizaciones POS: almacén correcto y factura única (UAT)

## Por qué ocurría

El módulo `ferreteria_pos_cotizaciones` creaba `sale.order` sin
`warehouse_id`. Odoo asignaba por defecto el almacén de Ventas (en las
capturas: «JB Central»), aunque el POS tenía como tipo de operación
«Palinche: Órdenes de PdV». Al confirmar, el módulo
`ferreteria_no_negative_stock_ferre` verificaba existencias contra el
almacén incorrecto. **No es seguro deshabilitar el control de existencias.**

## Nueva operación: POS es el único emisor de factura

1. En Punto de Venta → Ajustes → Inventario, comprobar **Tipo de operación**.
   El tipo de operación debe pertenecer al almacén de esa sucursal.
2. En POS, seleccionar cliente, productos, cantidades y precios.
3. **Crear cotización**. Se guarda en Ventas como borrador, ligada al
   almacén del tipo de operación y a la configuración del POS. **No reserva
   ni mueve mercancía, no genera pago y no crea factura.**
4. **Guardar cotización** deja el documento abierto para seguimiento.
5. **Confirmar y cobrar** (al crear o desde el selector de cotizaciones)
   carga el pedido mediante el motor nativo `pos_sale.settleSO`, con
   `sale_order_origin_id` y `sale_order_line_id` en todas las líneas
   importadas. Abre **Pago**, con **Factura** activada.
6. Al completar el pago, Odoo sincroniza: crea la orden POS, comprueba y
   mueve el inventario desde el almacén POS, genera **una factura POS** y
   confirma el pedido de Ventas mediante `pos_sale`. El módulo de stock
   ya no vuelve a exigir el stock que POS efectivamente entregó.
7. La factura POS conserva la relación con la cotización en
   `ferreteria_pos_sale_order_id`, y Ventas muestra el botón **Factura POS**.
   La factura POS, no una segunda factura de Ventas, es el documento fiscal.
8. No utilizar **Crear factura** en la orden de Ventas para esta
   operación. El vínculo POS evita emitir dos comprobantes al repetir
   el cobro, y detecta una factura previa creada manualmente desde Ventas.

### Protección de duplicidad

El backend bloquea el cobro de la misma cotización si ya existe una
orden POS pagada o una factura activa. Comprueba empresa/almacén y evita
mezclar artículos de cotizaciones distintas. El cobro de cotizaciones
propias requiere marcar **Factura** en la orden POS; el flujo automático
lo hace por defecto. El bloqueo PostgreSQL en la orden de venta serializa
las validaciones de cobros simultáneos.

Los productos añadidos sin enlace a la cotización no se incorporan al
cobro de la misma. Cree otra orden POS en caso de necesitar artículos
independientes.

## Checklist de pruebas con UAT (sin valor fiscal)

- [ ] El POS de Palinche crea cotización con almacén Palinche y no JB Central.
- [ ] **Guardar cotización** no crea `account.move`, `pos.order` pagada
      ni `stock.picking` nuevo.
- [ ] Desde nueva cotización, **Confirmar y cobrar** abre Pago e identifica
      al cliente correcto, precios, descuentos e impuestos.
- [ ] Desde la lista de cotizaciones, **Confirmar y cobrar** también abre Pago.
- [ ] El control de stock solo consulta la sucursal POS; cuando realmente
      no hay existencias, bloquea el pago.
- [ ] Pago completo con opción Factura crea **exactamente un** comprobante,
      una orden POS y una venta vinculada.
- [ ] En Ventas, el pedido está confirmado y muestra **Factura POS**;
      el UUID/serie fiscal no aparece duplicado en Contabilidad.
- [ ] El stock se descuenta **una vez** en Palinche y no en JB Central;
      el movimiento de Ventas residual se cancela/reduce mediante `pos_sale`.
- [ ] Intentar cobrar la misma cotización otra vez muestra bloqueo.
- [ ] Si se cancela el diálogo antes de pagar, no se generan ni factura
      ni transferencia; la cotización continúa como borrador.
- [ ] Cobros simultáneos en dos sesiones del mismo POS no duplican facturas.
- [ ] El guard de ventas directas sin stock sigue rechazando órdenes no POS.
- [ ] El módulo de Megaprint certifica **solo** la factura generada por POS.

**Antes de instalar:** respalde la base UAT. Actualice
`ferreteria_pos_cotizaciones` y `ferreteria_no_negative_stock_ferre`,
cierre y reabra las sesiones POS para refrescar JavaScript y datos cargados.

**Cotizaciones anteriores:** las que se generaron antes de esta versión
podrían seguir teniendo almacén JB Central y no tienen POS origen guardado.
Corrija su almacén explícitamente desde Ventas antes de intentar cobrarlas.
Nunca modifique el almacén de una venta ya entregada o facturada.

**Importante:** esta rama contiene la implementación propuesta, no una
validación completa en un servidor Odoo/contabilidad/FEL. No promover a
producción hasta completar el checklist en la base UAT.
