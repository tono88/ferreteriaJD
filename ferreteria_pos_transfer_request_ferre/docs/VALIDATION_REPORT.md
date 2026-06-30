# Informe de validación de la entrega

## Comprobaciones ejecutadas en el entorno de construcción

- Lectura del manifiesto con `ast.literal_eval`.
- Confirmación de existencia de archivos declarados en `data`, `demo` y `assets`.
- Compilación sintáctica de archivos Python.
- Análisis AST de archivos Python.
- Parseo XML de seguridad, datos, demo, vistas y plantillas OWL.
- Validación del CSV de accesos.
- Revisión de referencias XML locales.
- Búsqueda de `attrs` y `states` obsoletos.
- Búsqueda de nombres técnicos de pastelería en código ejecutable.
- Confirmación de ausencia de escrituras directas sobre `stock.quant` en código productivo.
- Revisión de los métodos RPC para impedir confiar en datos del navegador.
- Comprobación sintáctica de JavaScript con Node.js.
- Revisión de que el botón se inserta en el contenedor estándar de acciones de `ControlButtons`.
- Confirmación de que la creación POS termina en `Solicitada`, sin pickings ni reserva.
- Eliminación de `__pycache__` antes del empaquetado.

## Validación funcional conocida

El usuario confirmó manualmente en su base el flujo backend completo de la versión anterior: aprobación, reserva, despacho hacia tránsito y recepción en el almacén destino.

## Pruebas que deben ejecutarse en la instancia Odoo

El entorno de construcción no contiene el servicio Odoo/PostgreSQL del usuario. Por ello, aún deben ejecutarse en una copia de su base:

- actualización real del módulo;
- compilación/carga del bundle POS;
- apertura visual del menú de acciones;
- búsqueda y creación desde el diálogo OWL;
- pruebas automatizadas `post_install`.

La prueba visual es especialmente importante porque otros módulos personalizados del POS pueden extender el mismo componente.
