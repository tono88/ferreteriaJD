# Ferretería - Alertas de reabastecimiento por correo

## Función

Envía una alerta por correo a los usuarios seleccionados cuando el inventario pronosticado de una regla de reabastecimiento queda por debajo del mínimo configurado.

## Reglas

- Utiliza las reglas estándar `stock.warehouse.orderpoint` de Odoo 18.
- Evalúa `Pronóstico < Mínimo`, igual que el reabastecimiento estándar.
- Envía una sola alerta mientras la regla permanezca por debajo del mínimo.
- Cuando el pronóstico vuelve al mínimo o lo supera, la alerta se cierra automáticamente.
- Si posteriormente vuelve a bajar, se envía una nueva alerta.
- El correo incluye producto, almacén, ubicación, existencias, pronóstico, mínimo, máximo, cantidad sugerida y un botón para abrir el reabastecimiento en Odoo.

## Configuración

1. Configure un servidor de correo saliente SMTP en Odoo.
2. Vaya a Ajustes > Usuarios y compañías > Usuarios.
3. Abra cada usuario que deba recibir alertas.
4. En la pestaña **Alertas de inventario**, marque **Recibir alertas de reabastecimiento**.
5. Compruebe que el usuario tenga un correo válido.
6. Configure reglas estándar de reabastecimiento por producto y ubicación.

## Frecuencia

La acción programada se ejecuta cada hora. Para una prueba inmediata, abra la regla de reabastecimiento y pulse **Revisar alerta ahora**.

## Alcance de destinatarios

Todos los usuarios marcados reciben alertas de todas las reglas de la compañía a la que tengan acceso. El filtrado de destinatarios por almacén no forma parte de esta primera versión.
