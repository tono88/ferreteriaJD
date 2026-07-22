# Recuperación POS REV8

Módulo: `pos_internal_correlative_ferre`
Versión: `18.0.1.0.13`

Esta revisión elimina toda intervención frontend del módulo y la sobrescritura incorrecta de `_load_pos_data_fields()` sobre `pos.order`.

El correlativo continúa generándose en backend al crear la orden y copiándose a la factura. Temporalmente no se imprime en el recibo POS hasta completar una implementación aislada y probada después de recuperar la operación normal.
