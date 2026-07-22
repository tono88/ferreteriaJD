# Ferretería - Boleta bancaria única

Impide reutilizar un número de boleta bancaria dentro de la misma compañía entre:

- `account.payment.bank_reference`;
- `pos.order.payment.bank_slip_number`;
- `pos.order.payment.master.bank_slip_number`.

La comparación elimina espacios externos, normaliza Unicode y no distingue mayúsculas/minúsculas. Los registros históricos no se liberan al cancelar, eliminar o editar un pago.

## Instalación

La instalación revisa las referencias existentes en `account.payment`. Si encuentra duplicados, aborta y muestra los pagos que deben corregirse antes de volver a instalar.
