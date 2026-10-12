# Resultado de auditoría estática — 18.0.1.2.0

**Resultado:** 53/53 verificaciones estáticas PASS. **No implica homologación funcional**.

Evidencia verificada sobre los archivos del paquete:

- XML de seguridad y vistas válido, XML-ID de las reglas sin duplicados y versión correcta.
- Dominios 318/319/320 idénticos a 18.0.1.1.0 y banderas: `perm_read=False`, `perm_write=True`, `perm_create=True`, `perm_unlink=True`.
- Los dominios 321 y 322 coinciden carácter por carácter con los facilitados desde `COPIA_PRDO_CUIDADO`, tras el desescape XML de `&amp;`.
- Mismas reglas y dominios operativos preexistentes para `pos.order` / `pos.order.line` con read=False; nuevas reglas globales solo read, sin escribir/crear/eliminar.
- Usuario sin scope conserva dominio global; usuario con scope sin grupo lee sus POS; usuario con scope y nuevo grupo lee las compañías permitidas. Comprobado con simulaciones estáticas del evaluador de expresiones, no con el motor ORM de Odoo.
- ACL nuevas: `pos.order`, `pos.order.line`, `report.pos.order` conceden solo read.
- Sin cambios a los archivos Python existentes, vistas de usuario y grupos de solo consulta; ni a reglas de `pos.config`, `pos.session`, `pos.payment`, etc.
- Estructura lógica de dominios 321/322 válida a nivel sintáctico.

## Pendiente de homologación

No se dispone en este entorno de instancia Odoo 18, de acceso a `COPIA_PRDO_CUIDADO`, ni de los addons externos de reportes. Por tanto, **ninguna de las 13 pruebas funcionales solicitadas ha sido ejecutada**. La ejecución de XML bajo Odoo real, la evaluación de reglas ORM, la consulta de reportes, el comportamiento de relaciones `pos.session` / `pos.config` y la seguridad de rutas que utilicen `sudo()` deberán confirmarse en esa copia.

Estado de promoción: **NO APROBADO PARA PRODUCCIÓN**.
