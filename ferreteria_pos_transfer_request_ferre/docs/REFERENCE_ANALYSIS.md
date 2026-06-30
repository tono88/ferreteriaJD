# Análisis de los módulos de referencia

## `pasteleria_pos_transferencias`

### Componentes aprovechables conceptualmente

- Botón y acceso desde POS.
- Popup para elegir sucursal y productos.
- Consulta informativa de existencias.
- Captura de cantidades.
- Comunicación POS–backend.
- Creación de picking y movimientos.

Estos elementos se reservan para la Fase 2. No se copiaron activos JavaScript, modelos ni dependencias del módulo.

### Comportamientos descartados

- Al confirmar, el módulo de referencia crea el picking, lo asigna y lo valida inmediatamente.
- Crea líneas de operación exigiendo lote en todas las líneas.
- No separa aprobación, despacho y recepción.
- Solo maneja estados básicos de borrador, confirmado y cancelado.
- Su archivo de seguridad no implementa una segregación efectiva por sucursal.
- Tiene dependencias y terminología específicas de pastelería.

Ese flujo no satisface el tránsito en dos etapas ni la recepción obligatoria de la sucursal solicitante.

## `pasteleria_desechos`

### Componentes aprovechables conceptualmente

- Documento independiente con chatter.
- Separación entre solicitante y aprobador.
- Estados de solicitud, aprobación y rechazo.
- Observaciones y trazabilidad de usuarios/fechas.
- Grupos y reglas de acceso.

### Limitaciones corregidas en el nuevo diseño

- Su seguridad es general y no relaciona usuarios con almacenes autorizados.
- La confirmación también termina validando el movimiento de inventario inmediatamente.
- El manejo de lotes está acoplado al proceso de desechos.
- No existe recepción en una segunda sucursal ni una ubicación de tránsito.
- No contempla aprobación parcial, cantidades por etapa o incidencias posteriores al despacho.

## Decisión de reutilización

La implementación nueva reutiliza **patrones funcionales**, no código completo ni dependencias entre módulos. Toda la terminología, modelos, XML IDs, grupos y reglas son propios de ferretería. Los módulos de referencia permanecen fuera del `addons_path` activo.
