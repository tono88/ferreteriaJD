# partner_internal_code_import_ferre

Parche mínimo para Odoo 18 Community.

## Objetivo
Permitir que `res.partner.internal_code` aparezca como campo importable y acepte
los códigos preparados en la migración (`CLI-00001`, `CLI-00002`, etc.).

## Dependencia
- `partner_internal_code_v4_ferre`

## Qué cambia
Solo redefine el atributo ORM del campo:

    internal_code = fields.Char(readonly=False)

No toca POS, FEL, contabilidad, datos existentes, generación automática ni la
restricción de unicidad del módulo original.

## Instalación
1. Copiar la carpeta `partner_internal_code_import_ferre` al `addons_path`.
2. Reiniciar Odoo.
3. Actualizar la lista de aplicaciones.
4. Instalar `Partner Internal Code - Import Support (Ferre)`.
5. Confirmar que `Código interno` aparece en una exportación compatible con importación.
6. Volver al importador de clientes y mapear `internal_code` con `Código interno`.
7. Pulsar primero `Probar`.

## Después de la importación
Antes de retirar el parche, crear un contacto de prueba y validar que el siguiente
código automático no colisiona con los códigos `CLI-xxxxx` importados.

Si la secuencia del módulo original no avanzó durante la importación, deberá
sincronizarse con el último código importado. Este parche no adivina ni modifica
esa secuencia porque aquí no se dispone del código fuente exacto de
`partner_internal_code_v4_ferre`.

Una vez validada la secuencia, el parche puede desinstalarse para devolver
`internal_code` a su condición original de solo lectura.
