# Aprobación de descuentos POS (Odoo 18)

Adaptación de **POS Discount Manager Approval** de Cybrosys Technologies
(autor Bhagyadev KP, AGPL-3), manteniendo el límite por empleado.

## Configuración

1. Active **Iniciar sesión como empleado** en Punto de venta → Ajustes.
2. En **Empleados**, establezca **Límite de descuento (%)**, por ejemplo **1**
   para Ana Reyes. El valor 0 conserva la convención histórica: sin límite.
3. Cierre y vuelva a abrir la sesión POS para cargar el campo.
4. Aplique un **descuento por línea** o un **descuento global**.
5. En **Pago → Validar**, si se excede el límite combinado, el POS solicita
   el código generado por un gerente con `pos_discount_otp_generator`.
6. El código se valida contra el cajero actualmente conectado en POS;
   no contra la cuenta administrativa que abrió la sesión.
7. El código caduca en 10 minutos y se consume una sola vez.

## Qué cambia respecto a la versión inicial

La versión anterior comprobaba únicamente `pos.order.line.discount`.
En Odoo 18, `pos_discount` implementa los descuentos globales mediante una
línea con producto de descuento y precio negativo, que la implementación
anterior omitía. La nueva versión evalúa ambos tipos y el porcentaje total
combinado. Si no se ha cargado el campo de límite en el POS, bloquea la
validación en lugar de tratar el caso como descuento ilimitado.

## Prueba UAT

Con Ana Reyes (límite 1 %), agregue un producto y aplique 2 % global.
En Pago → Validar debe aparecer el diálogo de autorización. Con 0.5 % no
debería solicitar código. Repita aplicando 2 % por línea y 0.7 % por
línea + 0.7 % global. Haga pruebas de OTP incorrecto, correcto,
caducado y reutilizado.

**Alcance:** este control está en la pantalla POS del navegador, como en el
módulo original. No constituye una barrera completa ante clientes POS
modificados o integraciones que eviten la interfaz. Para seguridad fuerte,
añadir validación de descuentos del pedido en el servidor.

Código distribuido bajo AGPL-3; créditos: Cybrosys Technologies Pvt. Ltd.
