# Changelog

## 18.0.1.0.0 - 2026-07-21

- Agrega el campo `Recibir alertas de reabastecimiento` en usuarios.
- Revisa cada hora las reglas estándar de reabastecimiento.
- Envía correo al cruzar por debajo del mínimo.
- Evita correos duplicados mientras la alerta continúe activa.
- Cierra automáticamente la alerta cuando el inventario pronosticado se recupera.
- Agrega botón manual de prueba y campos de seguimiento en la regla.
- Incluye enlace directo al reabastecimiento en Odoo.

## 18.0.1.0.2 — 2026-07-21

- Se añadió evaluación inmediata al completar movimientos de inventario.
- La alerta se revisa automáticamente después de ventas POS, entregas, recepciones,
  transferencias internas, devoluciones y ajustes de inventario que generen movimientos.
- Solo se recalculan las reglas del producto, compañía y ubicación afectados.
- Se mantiene el cron de una hora como mecanismo de respaldo.
- Los errores de correo o notificación no revierten la operación de inventario.
- Se conserva el control de un único correo por ciclo bajo el mínimo.
