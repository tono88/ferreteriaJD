# Arquitectura técnica — Backend e integración POS

## 1. Modelo principal

`ferreteria.transfer.request`

Responsabilidades:

- Encabezado de la solicitud.
- Sucursales solicitante y suministradora.
- POS solicitante y cliente informativo.
- Máquina de estados.
- Auditoría de usuarios y fechas.
- Enlace a los dos pickings.
- Acciones transaccionales del flujo.
- Chatter y actividades manuales.
- Métodos RPC específicos para la interfaz POS.

Estados implementados:

`draft → submitted → review → approved/partial → preparing → dispatched → received/incident → closed`

Estados terminales alternativos: `rejected` y `cancelled`.

## 2. Líneas

`ferreteria.transfer.request.line`

Cada línea conserva:

- cantidad solicitada;
- cantidad aprobada;
- cantidad reservada;
- cantidad despachada;
- cantidad recibida;
- cantidad con incidencia;
- unidad de medida;
- movimiento de despacho;
- movimiento de recepción;
- existencia libre informativa del almacén suministrador.

Las restricciones impiden cantidades negativas y que una etapa supere a la anterior. La unidad de medida debe pertenecer a la categoría del producto.

## 3. Inventario y tránsito

Al aprobar:

1. Se crea un picking interno del almacén suministrador hacia `Tránsito entre sucursales`.
2. Se crea un picking interno desde tránsito hacia el almacén solicitante.
3. Cada movimiento de recepción se enlaza con su movimiento de despacho mediante `move_orig_ids`.
4. Se confirman ambos conjuntos de movimientos.
5. Solo el movimiento de despacho se asigna y reserva.
6. Si una línea no queda completamente reservada, la transacción se revierte.

Al despachar se valida únicamente el picking hacia tránsito. Al recibir se valida únicamente el picking desde tránsito. Una diferencia de recepción genera una incidencia y no se transforma en cancelación retroactiva.

No se escribe directamente en `stock.quant`.

## 4. Integración POS

La extensión del POS se divide en dos capas.

### Capa OWL

- `transfer_request_button.js` extiende `ControlButtons`.
- `transfer_request_button.xml` agrega la opción **Solicitudes a otras sucursales** al menú estándar de acciones.
- `transfer_request_popup.js` y `transfer_request_popup.xml` implementan el diálogo.
- `transfer_request.scss` contiene estilos responsivos.

El diálogo permite:

- ver el POS y la sucursal solicitante;
- seleccionar la sucursal suministradora;
- buscar productos almacenables existentes;
- consultar existencia libre informativa;
- agregar cantidades y observaciones;
- seleccionar un cliente existente de forma opcional;
- enviar la solicitud;
- consultar estados recientes.

### Capa servidor

`models/pos_transfer_request.py` expone métodos RPC controlados:

- `pos_get_request_ui_data`;
- `pos_search_request_products`;
- `pos_search_request_partners`;
- `pos_create_request_from_ui`;
- `pos_get_recent_requests`.

Cada llamada valida nuevamente:

- usuario y grupos;
- compañía activa;
- POS existente;
- almacén relacionado con el POS;
- autorización del usuario sobre dicho almacén;
- sucursal suministradora distinta;
- productos activos y almacenables;
- cantidades positivas y finitas;
- cliente compatible con la compañía.

La interfaz nunca envía directamente valores de reserva o movimientos. Crear desde POS equivale a crear y enviar una solicitud backend: queda en `submitted`, sin pickings y sin reserva.

## 5. Productos

En backend se desactiva la creación rápida y la edición desde el selector de producto de las líneas. En POS solo se buscan registros existentes con `is_storable=True`. Esto evita crear accidentalmente servicios o bienes sin seguimiento de inventario desde el proceso de solicitud.

## 6. Lotes y números de serie

La solicitud no captura lote o serie. Para productos con seguimiento, los datos se completan en las operaciones detalladas estándar de los pickings antes del despacho y recepción.

## 7. Seguridad

Grupos técnicos:

- Solicitante de productos.
- Aprobador de sucursal.
- Despachador de sucursal.
- Receptor de sucursal.
- Administrador de solicitudes.

La configuración funcional se guarda en `ferreteria.transfer.user.permission`, con registros por usuario que pueden abarcar varias sucursales y varios POS. Las banderas `can_request`, `can_approve`, `can_dispatch` y `can_receive` generan alcances independientes en `res.users` y sincronizan automáticamente los grupos técnicos.

Para **Solicitar**, un POS específico limita el permiso a ese POS; una línea sin POS representa autorización general para todos los POS del almacén. Aprobación, despacho y recepción se validan contra el almacén porque los movimientos de inventario pertenecen a la sucursal.

La seguridad se aplica mediante reglas de registros y comprobaciones Python. El botón POS permanece visible para mantener una interfaz consistente, pero la operación se bloquea en servidor cuando el usuario no está autorizado para el POS actual.

Los pickings vinculados no pueden validarse, cancelarse, desreservarse, desvincularse ni eliminarse directamente.

## 8. Consistencia y concurrencia

Antes de las acciones críticas se ejecuta un bloqueo `SELECT ... FOR UPDATE` sobre la solicitud. Los estados y los pickings se vuelven a comprobar dentro de la misma transacción, evitando dobles aprobaciones, despachos o recepciones.

## 9. Incidencias

`ferreteria.transfer.incident` conserva cantidad despachada, recibida y afectada, tipo, usuario, fechas, observación y resolución. No genera mermas, ajustes contables ni asientos.
