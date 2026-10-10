# Aprobación de descuentos POS (Odoo 18) — 2.2.0

Adaptación de **POS Discount Manager Approval** de Cybrosys Technologies,
AGPL-3. Mantiene el límite porcentual por empleado y añade códigos OTP
individuales, aleatorios y de un solo uso mediante `pos_discount_otp_generator`.

## Dos modalidades de identificación

### A. Selección de empleados Odoo (`module_pos_hr = True`)

Activar **Iniciar sesión como empleado** en los ajustes del POS. El cajero
elige empleado, inicia sesión con su PIN/credencial y se utiliza el campo
**Límite de descuento (%)** de esa ficha.

### B. Cajero único por cuenta de Odoo (sin PIN adicional)

Instalar opcionalmente **`ferreteria_pos_cajero_unico_ferre`**. Cerrar la
sesión POS, desactivar **Iniciar sesión como empleado** y activar
**Cajero único según cuenta de Odoo** en cada configuración de POS elegida.

Cada usuario POS debe tener una cuenta Odoo propia y un único empleado activo
vinculado mediante **Empleados → Ajustes de RR. HH. → Usuario relacionado**,
dentro de la misma empresa del POS. El POS se abre directamente bajo esa cuenta,
sin PIN adicional ni posibilidad de cambiar a otro cajero en la interfaz.

En esta modalidad el servidor asocia la cuenta autenticada a su empleado
mediante `get_logged_user_discount_policy`. El navegador **nunca decide**
qué empleado corresponde a la cuenta para emitir autorización. El OTP se consume
mediante `consume_code_for_logged_user`, reutilizando la validación segura de
un solo uso del generador original.

**Condición de sesión:** el canje OTP del generador actual requiere una sesión
POS `opened` cuyo `user_id` sea el mismo usuario autenticado que cobra.
Cuando una caja es abierta por otro usuario el canje no procede; se debe abrir
la sesión con el cajero autenticado. Esto evita ampliar permisos de manera
implícita.

**Cierre de caja básico:** como `module_pos_hr` se desactiva para ese POS,
el estándar de Odoo muestra **Cerrar caja** a usuarios con acceso normal al POS.
Las diferencias de arqueo mayores que el máximo autorizado siguen exigiendo
permiso de gerente. No se amplían ACL de Contabilidad ni se permite saltar
el cierre contable habitual.

## Autorización por descuento

1. Ajustar **Límite de descuento (%)** en Empleados: por ejemplo 1 para Ana.
2. Aplicar un descuento de línea o global; también se detectan combinaciones.
3. Entrar en **Pago → Validar**.
4. Si el porcentaje efectivo excede el límite, aparece autorización del cajero.
5. El gerente genera código en **Punto de venta → Códigos para descuentos**,
   seleccionando el empleado y el POS correspondiente.
6. El cajero introduce los seis dígitos. El código vence a los 10 minutos y
   solo se puede usar una vez. Al generar otro o fallar cinco veces, se invalida.

Un límite de **0** conserva la convención original: **sin límite**. Si no hay
un empleado correcto, falla la consulta al servidor, o no se ha cargado la
política, el POS no permite finalizar esa operación. Por lo tanto, con cajero
único se necesita conectividad al validar cada venta.

## Pruebas UAT

- Ana con límite 1%, descuento 0.5%: no debe solicitar OTP.
- Ana con descuento global o individual de 5%: debe solicitar OTP.
- Dos descuentos de 0.7% (línea+global) juntos: solicitan OTP.
- OTP ya utilizado, vencido, de otra sucursal o de otro empleado: rechazar.
- Cambiar de usuario de Odoo, abrir su propia sesión POS y comprobar que
  el límite se resuelve a su empleado, nunca al anterior.
- Comprobar cierre de caja con arqueo correcto como usuario básico y rechazo
  de una diferencia mayor que el límite de la empresa.
- Comprobar que la modalidad `module_pos_hr=True` conserva comportamiento.

**Alcance:** el control porcentual se ejecuta en la interfaz POS del navegador
(como en el addon de origen), no es una regla universal sobre pedidos generados
por clientes alterados u otras integraciones. Para una barrera antifraude
completa, la regla requiere validación de porcentaje también en backend.

Código AGPL-3 con atribución original a Cybrosys Technologies Pvt. Ltd.
