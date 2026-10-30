# Changelog

## 18.0.1.2.0 — 2026-10-29

- Agrega recuperación explícita de reservas de pagos cancelados o eliminados.
- Restringe la recuperación a administradores contables o de sistema, con motivo obligatorio.
- Conserva auditoría del origen anterior y los pagos sustitutos sin borrar la reserva.
- Bloquea recuperación si hay pagos activos y reactivación de pagos sustituidos.
- Explica en el error cuando el bloqueo corresponde a una reserva histórica.
- Evita que el verificador antiguo devuelva un aviso ignorado y deje asientos en borrador.
- Revierte el registro si algún asiento de pago no quedó publicado.
- Añade pruebas para cancelación, eliminación, permisos, reversión y pagos activos.

## 18.0.1.0.0 — 2026-07-20

- Crea un registro central histórico de boletas bancarias.
- Añade unicidad fuerte por compañía mediante constraint PostgreSQL.
- Normaliza espacios externos, Unicode y mayúsculas/minúsculas.
- Integra pagos contables, pagos manuales POS y pagos maestros POS.
- Agrega validación en creación y edición.
- Incluye auditoría de referencias contables existentes durante la instalación.
