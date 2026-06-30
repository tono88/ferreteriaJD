# Ferretería — Solicitudes entre sucursales

Módulo para Odoo 18 Community que implementa el flujo backend y la creación de solicitudes desde el Punto de Venta para transferir productos entre sucursales de una misma compañía.

## Alcance de la versión 18.0.2.3.0

### Backend

- Solicitudes con una o varias líneas, cliente opcional y observaciones.
- Sucursal solicitante y sucursal suministradora.
- Aprobación total o parcial.
- Reserva inmediata del stock aprobado mediante `stock.picking` y `stock.move`.
- Dos operaciones separadas mediante la ubicación virtual `Tránsito entre sucursales`:
  1. almacén suministrador → tránsito;
  2. tránsito → almacén solicitante.
- Confirmación independiente de despacho y recepción.
- Registro y resolución de incidencias posteriores al despacho.
- Seguridad mediante una matriz de permisos por usuario, sucursal y punto de venta.
- Chatter, trazabilidad de usuarios y fechas, filtros y accesos a pickings.

### Punto de Venta

- Opción permanente **Solicitudes a otras sucursales** dentro del menú **Acciones** del POS.
- La sucursal solicitante se obtiene automáticamente del almacén relacionado con el POS actual.
- Selector de sucursal suministradora.
- Búsqueda predictiva de productos almacenables por nombre, referencia interna o código de barras.
- Sugerencias automáticas mientras se escribe, selección con ratón o teclado y prioridad para coincidencias exactas de códigos.
- Existencia libre informativa de la sucursal suministradora.
- Cantidad, observación por línea, cliente opcional y observación general.
- Envío directo de la solicitud al estado **Solicitada**.
- Consulta de las solicitudes recientes creadas por el usuario desde ese POS.
- La lógica crítica y los permisos se validan nuevamente en el servidor.


## Configuración de permisos 18.0.2.3.0

La configuración se encuentra en:

**Inventario → Solicitudes entre sucursales → Permisos por usuario y sucursal**

La vista solo está disponible para usuarios con permisos de **Administración/Ajustes** de Odoo. También aparece dentro de cada usuario, en la pestaña **Solicitudes entre sucursales**.

Cada registro permite seleccionar:

- uno o varios **almacenes/sucursales**;
- uno o varios **puntos de venta**;
- **Solicitar**;
- **Aprobar / rechazar**;
- **Preparar / despachar**;
- **Recibir / cerrar**.

Los selectores no dependen de una sucursal previamente elegida y no usan dominios de compañía en el formulario. Por ello el administrador puede ver todas las sucursales y todos los POS disponibles en la base.

Para **Solicitar**, si se eligen POS específicos, el permiso se limita a esos POS. Si la lista de POS queda vacía, el permiso aplica a todos los POS asociados a las sucursales seleccionadas. Los permisos de aprobar, despachar y recibir se validan por sucursal/almacén.

Los grupos técnicos se sincronizan automáticamente. El rol **Administrador de solicitudes** conserva acceso operativo total a las solicitudes, pero la configuración de usuarios queda reservada al administrador de Odoo.

## Reglas relevantes

- Desde las líneas de solicitud no se permite crear ni editar productos nuevos.
- Solo aparecen productos activos con seguimiento de inventario (`is_storable`).
- Enviar desde el POS no crea ni reserva movimientos de inventario.
- La reserva continúa ocurriendo únicamente cuando un aprobador confirma la solicitud en backend.
- La existencia mostrada en POS es informativa; se vuelve a comprobar al aprobar.
- El botón permanece visible en el POS, pero el servidor exige el permiso **Solicitar** para el POS actual.

## Fuera de alcance

No incluye facturación, FEL, ventas, pagos, listas de precios, descuentos, generación automática de lotes, notificaciones, actividades automáticas, SLA ni procesos contables por pérdidas.

## Dependencias

- `mail`
- `stock`
- `point_of_sale`

## Documentación

- `docs/REFERENCE_ANALYSIS.md`
- `docs/ARCHITECTURE.md`
- `docs/INSTALLATION.md`
- `docs/TEST_DATA.md`
- `docs/TEST_PLAN.md`
- `docs/VALIDATION_REPORT.md`
- `docs/KNOWN_RISKS.md`
- `docs/FILE_TREE.md`
- `CHANGELOG.md`


## Mejora 18.0.2.1.0

Sustituye la búsqueda en dos pasos por un autocompletado directo en el POS. Al escribir se muestran sugerencias con nombre, referencia interna, código de barras, seguimiento, unidad y existencia libre de la sucursal suministradora. Las coincidencias exactas de referencia o código de barras se priorizan.

## Corrección 18.0.2.0.1

Corrige un error de compilación de estilos del POS causado por una función SCSS `min()` con unidades `px` y `vw`. No cambia la lógica funcional de solicitudes, reservas, despachos o recepciones.

### Relación entre POS y sucursal

Desde la versión 18.0.2.3.1, la sucursal de un punto de venta se resuelve desde
el almacén de su **Tipo de operación**. Los almacenes derivados de POS se usan
internamente para validar permisos, pero no se copian automáticamente al campo
visible de almacenes seleccionados.
