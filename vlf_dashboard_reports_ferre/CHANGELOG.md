# Changelog

## 18.0.1.0.4

- Corrige el filtro de sucursal en tarjetas basadas en `pos.order.line`.
- Valida rutas relacionales completas antes de agregar dominios.
- Ignora valores `False` enviados por filtros de selección en estado “Todos”.
- Desactiva las tarjetas antiguas duplicadas “Top productos POS” en los dashboards administrados.

## 18.0.1.0.3
- Elimina del ORM los modelos técnicos `vlf.dashboard.metric.service` y `vlf.dashboard.preset.registry`.
- Convierte ambos componentes en servicios Python puros que reciben `env`.
- Corrige de raíz el `KeyError: vlf.dashboard.metric.service` durante `init_models`.

## 18.0.1.0.2
- Convierte `vlf.dashboard.metric.service` y `vlf.dashboard.preset.registry` en modelos técnicos concretos (`models.Model`) sin tabla (`_auto = False`).
- Evita que Odoo 18 elimine o no conserve los servicios durante la reconstrucción del registro ORM.
- Sustituye la corrección incompleta de 18.0.1.0.1, que únicamente agregaba `_register = True` a modelos abstractos.

## 18.0.1.0.1

- Corrige el registro ORM de los servicios abstractos `vlf.dashboard.metric.service` y `vlf.dashboard.preset.registry` en Odoo 18 mediante `_register = True`.
- Evita el `KeyError: vlf.dashboard.metric.service` durante la instalación inicial.

# 18.0.1.0.0

- Primera entrega funcional.
- Capa consolidada de ventas operativas.
- Métricas oficiales para Ventas Generales, POS y Ejecutivo Gerencial.
- Regla explícita de no duplicidad entre POS/Ventas y facturación.
- Presets versionados y actualizables.
- Correcciones del motor genérico de fechas, acumulados, totales e inventario interno.
