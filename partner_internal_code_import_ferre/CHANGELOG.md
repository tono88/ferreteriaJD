# Changelog

## 18.0.1.0.0 — 2026-08-10

- Habilita la importación de `res.partner.internal_code`.
- Cambia únicamente `readonly` a `False` a nivel ORM.
- No reemplaza la generación automática del módulo original.
- No modifica la restricción de unicidad ni los datos existentes.
- Se entrega como parche de migración reversible.
