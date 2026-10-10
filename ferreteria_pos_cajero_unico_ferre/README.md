# Ferretería JD — Cajero único por cuenta de Odoo (Odoo 18 Community)

El formulario de PIN y el selector de cajeros mostrados en la captura del usuario
son **funcionalidad estándar** de `pos_hr`, no de Discount Manager.

## Objetivo

Una cuenta Odoo = un cajero. No se permiten cambios entre empleados,
ni un PIN adicional en el POS. Los permisos reales y el nombre del cajero
corresponden al **usuario autenticado** y a su **empleado asociado**.

En este modo se usa el funcionamiento nativo de POS SIN `module_pos_hr`:
por ello **Cerrar caja** vuelve a estar disponible para usuarios de POS
básicos y los supervisores conservan la validación de diferencias superiores
a la tolerancia permitida.

## Configuración por punto de venta

1. Respaldar UAT y **cerrar correctamente la sesión POS**.
2. Cada cajero debe tener **una cuenta Odoo propia** con grupo
   **Punto de venta / Usuario** y **un empleado activo** de la misma empresa,
   enlazado en *Empleados → Ajustes de RR. HH. → Usuario relacionado*.
3. Asignar el **Límite de descuento (%)** a ese empleado, no a res.users.
4. Desde *Punto de venta → Ajustes → [POS]* desactivar
   **Iniciar sesión como empleado** (`module_pos_hr = False`).
5. Activar **Cajero único según cuenta de Odoo**.
6. Guardar, actualizar módulo, reiniciar sesión del POS y refrescar.
7. Ingresar a Odoo con la cuenta propia del cajero y abrir el POS:
   entra directamente a productos, sin selector de cajeros ni PIN.
8. Para cerrar: menú superior derecho → **Cerrar caja**.
   El usuario básico puede hacer arqueo y cerrar con diferencias dentro
   de tolerancia; una diferencia excesiva sigue requiriendo al gerente.

**Importante:** cada persona debe ingresar con credenciales de Odoo únicas
(no compartir contraseñas). Si la cuenta carece de empleado asociado,
Discount Manager no permitirá validar cobros (política que falla en cerrado).
Las autorizaciones OTP se generan desde **Punto de venta → Códigos para
descuentos** para ese empleado y POS; mantienen caducidad de 10 minutos,
un solo uso y el límite asignado.

La verificación de descuentos del módulo permanece en frontend POS;
no reemplaza validaciones obligatorias de backend ante un cliente alterado.

La integración no se aplica a otros POS: opción desmarcada = flujo original.
Si desea volver a la selección de empleados con PIN, primero desmarque
**Cajero único** (cerrando la sesión) y vuelva a activar `module_pos_hr`.
