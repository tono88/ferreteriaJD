# Plan de pruebas funcionales

## A. Instalación, actualización y permisos

1. Actualizar en una copia de la base.
2. Confirmar que el módulo muestra versión `18.0.2.0.0`.
3. Asignar al usuario que abre el POS el grupo **Solicitante de productos**.
4. Agregar a ese usuario el almacén correspondiente al POS.
5. Confirmar que usuarios no autorizados ven la opción, pero reciben un error del servidor al abrirla.
6. Verificar que aprobadores y receptores continúan limitados por sus almacenes.

## B. Selector de productos backend

1. Crear una solicitud backend y agregar una línea.
2. Comprobar que no aparecen las opciones **Crear** ni **Crear y editar** desde el selector.
3. Confirmar que los productos almacenables existentes sí pueden seleccionarse.

## C. Aparición del botón POS

1. Cerrar todas las pestañas del POS después de actualizar.
2. Ejecutar `Ctrl + F5` y abrir una sesión.
3. Abrir el menú **Acciones** o menú de tres barras.
4. Confirmar que aparece **Solicitudes a otras sucursales** siempre, sin depender de una orden o cliente.
5. Abrirlo y comprobar que muestra el POS y la sucursal solicitante correctos.

## D. Solicitud desde POS

1. Seleccionar una sucursal suministradora distinta.
2. Buscar por nombre, código interno y código de barras.
3. Confirmar que aparecen productos almacenables y no servicios/bienes sin seguimiento de inventario.
4. Confirmar que se muestra la existencia libre de la sucursal seleccionada.
5. Agregar uno o varios productos y modificar cantidades.
6. Agregar cliente opcional y observaciones.
7. Enviar la solicitud.
8. Verificar mensaje de éxito y cambio automático a **Mis solicitudes**.
9. Verificar en backend:
   - estado `Solicitada`;
   - POS y almacén solicitante correctos;
   - sucursal suministradora correcta;
   - usuario solicitante correcto;
   - líneas y cantidades correctas;
   - ningún picking creado;
   - ninguna reserva realizada.

## E. Consulta de estados en POS

1. Abrir **Mis solicitudes**.
2. Confirmar que solo se muestran las solicitudes creadas por el usuario actual desde ese POS.
3. Aprobar la solicitud desde backend.
4. Presionar **Actualizar** en POS y comprobar cantidades aprobadas y estado.
5. Repetir después del despacho y recepción.

## F. Disponibilidad y concurrencia

1. Solicitar una cantidad mayor a la existencia mostrada; el POS debe advertir, pero permitir enviar.
2. Intentar aprobarla en backend; la reserva debe impedir aprobar más de lo disponible.
3. Cambiar existencias después de consultar el POS y antes de aprobar; el servidor debe usar la disponibilidad actual.

## G. Flujo backend de regresión

1. Aprobación completa y parcial.
2. Reserva sin validación automática.
3. Despacho solo hacia tránsito.
4. Recepción obligatoria en destino.
5. Diferencia de recepción e incidencia.
6. Rechazo antes del despacho y liberación de reserva.
7. Protección frente a validación manual de pickings.

## H. Lotes y series

1. Producto sin seguimiento: flujo completo.
2. Producto por lote: completar lote en operaciones detalladas antes del despacho/recepción.
3. Producto por serie: asignar una serie por unidad.
4. Confirmar que el diálogo POS no obliga a seleccionar lote durante la solicitud.

## Pruebas automatizadas incluidas

`tests/test_transfer_request.py` cubre:

- flujo backend completo;
- protección del picking;
- aprobación parcial y recepción corta con incidencia;
- bloqueo de aprobación desde un almacén no autorizado;
- dominio y valor predeterminado del almacén solicitante;
- obtención de sucursal desde el POS;
- filtrado de productos almacenables en la búsqueda POS;
- creación y envío desde POS sin movimientos ni reserva;
- bloqueo de un solicitante no autorizado para el almacén del POS.
