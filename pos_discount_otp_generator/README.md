# Generador de códigos de descuento (Odoo 18)

Módulo **independiente** para gerentes: Punto de venta → Códigos para descuentos.
Seleccione cajero y POS; pulse **Generar código**. Comparta manualmente el código
de seis dígitos o use **Enviar al correo del cajero** (requiere correo laboral y SMTP).
Los códigos caducan en 10 minutos y se invalidan al usar, superar cinco intentos
fallidos o generar un código nuevo para el mismo cajero/POS.

No se guarda el código en texto plano en el historial persistente de autorizaciones:
solo un hash con sal individual. El asistente transitorio sí muestra temporalmente
el código al gerente para poder compartirlo. Solo un usuario con rol de gerente POS
puede generar; el canje exige una sesión POS abierta del usuario conectado.

El módulo `pos_discount_manager` proporciona la validación en la pantalla de pago;
sin él, el generador por sí solo no modifica el proceso de cobro.
