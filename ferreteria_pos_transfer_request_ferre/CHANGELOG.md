# Changelog

## 18.0.2.3.0 — Selectores múltiples y administración sin dominios

- Corrige los selectores vacíos de sucursal y POS causados por el alcance de compañía aplicado antes de seleccionar una sucursal.
- Sustituye los campos individuales por selectores múltiples de **Sucursales / almacenes** y **Puntos de venta**.
- El formulario de permisos muestra todos los almacenes y todos los POS visibles para el administrador, sin dominios dependientes entre campos.
- La vista y la pestaña de configuración quedan disponibles únicamente para administradores de Odoo.
- Un mismo registro puede autorizar varias sucursales y varios POS con el mismo conjunto de funciones.
- Si se selecciona un POS, su almacén se incorpora automáticamente al alcance de sucursales.
- Mantiene compatibilidad con las líneas de permisos anteriores y migra sus valores a los nuevos campos múltiples.
- Conserva la regla: con POS específicos, Solicitar se limita a esos POS; sin POS, aplica a todos los POS de las sucursales seleccionadas.
- Agrega pruebas para alcances múltiples y para permisos generales de sucursal.

## 18.0.2.2.0 — Permisos por sucursal y punto de venta

- Agrega la vista **Permisos por sucursal** para configurar cada usuario desde una matriz operativa.
- Permite asignar por sucursal/POS los permisos: **Solicitar**, **Aprobar/Rechazar**, **Preparar/Despachar** y **Recibir/Cerrar**.
- Agrega el rol técnico separado **Despachador de sucursal**.
- Sincroniza automáticamente los grupos técnicos según la matriz; ya no es necesario asignarlos manualmente.
- Limita las solicitudes del POS al punto de venta autorizado; una línea sin POS aplica a todos los POS de la sucursal.
- Actualiza reglas de registro y validaciones Python para usar alcances diferentes por función.
- Migra la lista anterior de almacenes autorizados a permisos generales de sucursal, conservando los roles existentes.
- Agrega pruebas para permisos exactos por POS y sincronización de grupos.

## 18.0.2.1.0 — Búsqueda predictiva de productos en POS

- Sustituye el selector separado por una lista de sugerencias directamente debajo del campo de búsqueda.
- Ejecuta la búsqueda automáticamente 280 ms después de escribir, evitando una llamada al servidor por cada tecla.
- Permite buscar por nombre, referencia interna estándar de Odoo (`default_code`) y código de barras.
- Prioriza coincidencias exactas de código de barras y referencia interna, seguidas de prefijos y coincidencias parciales.
- Permite navegar las sugerencias con flechas, seleccionar con Enter o hacer clic con el ratón.
- Muestra en cada sugerencia la existencia libre informativa, unidad de medida y seguimiento.
- Mantiene toda la validación crítica y el cálculo de existencia en el servidor.
- Agrega pruebas para búsqueda por nombre, referencia interna y código de barras.

## 18.0.2.0.1

- Corrige la compilación SCSS del POS eliminando `min(1100px, 88vw)`, que hacía que el compilador Sass intentara comparar unidades incompatibles (`px` y `vw`).
- Mantiene el ancho adaptable mediante `width: 88vw` y `max-width: 1100px`.
- Ajusta la versión móvil a `width: 100%` y `max-width: 100%`.
- Sustituye `align-items: end` por `align-items: flex-end` para mayor compatibilidad.

# Registro de cambios

## 18.0.2.0.0 — Fase 2 integración POS

- Se agregó la opción permanente **Solicitudes a otras sucursales** al menú de acciones del Punto de Venta.
- Se agregó un diálogo OWL para seleccionar sucursal suministradora, productos, cantidades, cliente opcional y observaciones.
- La sucursal solicitante se deriva del almacén asociado al POS actual.
- Se agregó búsqueda RPC de productos almacenables con existencia libre informativa por almacén.
- La solicitud creada desde POS se envía al estado `Solicitada` sin crear movimientos ni reservas.
- Se agregó una pestaña para consultar estados recientes desde el POS.
- Se incorporaron validaciones de servidor para usuario, compañía, POS, almacenes, productos, cantidades y cliente.
- Se bloqueó la creación rápida y la edición de productos desde las líneas backend de la solicitud.
- Se agregaron pruebas automatizadas de la API POS, filtrado de productos y permisos por almacén.

## 18.0.1.0.1 — Corrección de selección de sucursal y POS

- Se sustituyó el dominio web dependiente de un many2many calculado por un dominio de servidor por usuario y compañía.
- La sucursal solicitante se completa automáticamente cuando el usuario solo tiene una sucursal autorizada.
- Al seleccionar un punto de venta, su almacén se establece como sucursal solicitante.
- El selector de punto de venta muestra los POS de la compañía incluso antes de seleccionar la sucursal.
- Al cambiar de sucursal se limpia un POS que pertenezca a otro almacén.
- La creación RPC puede derivar la sucursal solicitante a partir del punto de venta.

## 18.0.1.0.0 — Fase 1 backend

- Creación de los modelos de solicitud, líneas e incidencias.
- Máquina de estados desde borrador hasta cierre.
- Aprobación total y parcial con validaciones por unidad de medida.
- Creación de pickings encadenados de despacho y recepción.
- Reserva estándar del inventario al aprobar.
- Confirmación independiente de despacho y recepción.
- Ubicación compartida `Tránsito entre sucursales`.
- Incidencias manuales y automáticas por faltantes de recepción.
- Grupos, permisos, reglas de registro y almacenes autorizados por usuario.
- Validaciones Python para impedir acciones por sucursal no autorizada.
- Protección contra dobles aprobaciones, despachos y recepciones.
- Bloqueo de validación, cancelación, liberación o eliminación directa de los pickings vinculados.
- Vistas backend, filtros, chatter y trazabilidad.
- Datos demo básicos y pruebas automatizadas.

## 18.0.2.3.1

- Corrige la relación POS → almacén tomando como fuente de verdad el almacén del
  **Tipo de operación** (`picking_type_id.warehouse_id`).
- Evita copiar automáticamente el almacén del POS a las etiquetas visibles de
  `Sucursales / almacenes`.
- Tolera bases donde el campo almacenado `pos.config.warehouse_id` esté
  desactualizado o conserve el almacén predeterminado de la compañía.
- Aplica la misma resolución al permiso, creación backend y creación desde POS.
