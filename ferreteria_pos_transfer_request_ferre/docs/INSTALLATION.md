# Instalación y actualización

## Instalación inicial

1. Realizar copia de seguridad de la base de datos y del filestore.
2. Copiar la carpeta `ferreteria_pos_transfer_request` dentro de un directorio incluido en `addons_path`.
3. Reiniciar el servicio de Odoo.
4. Activar modo desarrollador y actualizar la lista de aplicaciones.
5. Buscar **Ferretería - Solicitudes entre sucursales** e instalar.
6. En cada usuario, asignar los grupos del módulo y configurar **Almacenes autorizados para solicitudes**.
7. Verificar que cada POS esté relacionado con el almacén correcto mediante su tipo de operación.
8. Cerrar y volver a abrir cualquier sesión o pestaña del POS para cargar los nuevos assets.

## Actualización desde una versión anterior

1. Respaldar la base de datos y la carpeta anterior del módulo.
2. Detener el servicio de Odoo.
3. Sustituir completamente la carpeta `ferreteria_pos_transfer_request`; no dejar una carpeta duplicada dentro de otra.
4. Iniciar Odoo.
5. Abrir **Aplicaciones**, actualizar la lista y presionar **Actualizar** sobre el módulo.
6. Cerrar todas las pestañas del POS.
7. Ejecutar una recarga completa del navegador con `Ctrl + F5` y abrir de nuevo el POS.
8. Si los assets antiguos siguen almacenados, abrir temporalmente Odoo con `?debug=assets`, recargar y volver a entrar al POS.

No se debe desinstalar el módulo para actualizarlo.

## Actualización por consola en Windows

```bat
"C:\Program Files\Odoo 18.0.20250520\python\python.exe" ^
"C:\Program Files\Odoo 18.0.20250520\server\odoo-bin" ^
-c "C:\Program Files\Odoo 18.0.20250520\server\odoo.conf" ^
-d NOMBRE_BASE ^
-u ferreteria_pos_transfer_request ^
--stop-after-init
```

Después debe iniciarse nuevamente el servicio normal de Odoo.

## Configuración mínima de usuarios

- Usuario que abre el POS: permisos normales de Punto de Venta, grupo **Solicitante de productos** y el almacén del POS incluido en **Almacenes autorizados para solicitudes**.
- Aprobador/despachador: grupo **Aprobador de sucursal** y almacén suministrador autorizado.
- Receptor: grupo **Receptor de sucursal** y almacén destino autorizado.
- Administrador: grupo **Administrador de solicitudes**; puede actuar sobre todas las solicitudes de la compañía actual.

El botón del POS se muestra siempre en **Acciones**, pero las llamadas al servidor se rechazan cuando el usuario no tiene permiso o el almacén del POS no está autorizado.
