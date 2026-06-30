# Instrucciones de actualización e instalación

## Ruta activa confirmada

```text
C:\Program Files\Odoo 18.0.20250520\server\odoo\addons
```

## Procedimiento

1. Detener el servicio `odoo-server-18.0`.
2. Copiar la carpeta completa `megaprint_fel_credentials_test` en la ruta activa de addons.
3. Iniciar el servicio `odoo-server-18.0`.
4. Ingresar a Odoo como administrador.
5. Activar el modo desarrollador.
6. Ir a Aplicaciones y ejecutar **Actualizar lista de aplicaciones**.
7. Quitar el filtro “Aplicaciones”, buscar `Megaprint FEL - Prueba segura de credenciales` e instalarlo.
8. Confirmar que la compañía mantiene activo **Modo de Pruebas FEL**.
9. Abrir el diario FEL y ejecutar la prueba.

## No realizar durante esta fase

- No cambiar a producción.
- No emitir una factura para probar credenciales.
- No reemplazar `fel_megaprint`.
- No desinstalar módulos FEL actuales.
- No modificar la base de datos mediante SQL.

## Evidencia solicitada después de la prueba

Enviar una captura completa del modal de resultado. No enviar la API key ni editarla para mostrarla.
