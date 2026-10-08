# Aprobación de descuentos POS (Odoo 18)

Adaptación de **POS Discount Manager Approval** de Cybrosys Technologies
(autor Bhagyadev KP, AGPL-3), manteniendo el límite por empleado.

El módulo original comprobaba el PIN estático del superior en la pantalla
de pago. Esta adaptación elimina esa validación y utiliza el módulo
independiente `pos_discount_otp_generator`: códigos numéricos de seis dígitos,
válidos por diez minutos y de un solo uso, validados en el servidor.

**Uso:** configure el campo *Límite de descuento (%)* en el empleado, genere
un código para ese cajero y punto de venta desde el menú de gerentes,
comparta el código con el cajero y autorice al finalizar el cobro.

**Compatibilidad:** Odoo 18; requiere `pos_discount`, `pos_hr`
y `pos_discount_otp_generator`. Un límite de 0 equivale a **sin límite**
(comportamiento heredado del módulo). Esta verificación se aplica en el
cliente POS antes de validar la orden; no sustituye la política de
autorizaciones del backend ni protege otros canales de venta.

Código distribuido bajo AGPL-3; créditos: Cybrosys Technologies Pvt. Ltd.
