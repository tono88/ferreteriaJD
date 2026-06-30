# Megaprint FEL - Prueba segura de credenciales

Módulo auxiliar para Odoo 18 Community que agrega el botón **Probar credenciales FEL** al formulario de diarios contables configurados con `fel_megaprint`.

## Alcance

La prueba realiza exclusivamente una solicitud de token al endpoint QA autorizado:

```text
https://dev2.api.ifacere-fel.com/api/solicitarToken
```

No crea facturas, no contabiliza, no procesa órdenes POS y no genera movimientos de inventario.

## Controles de seguridad

- Bloquea la llamada si la compañía no tiene activo **Modo de Pruebas FEL**.
- Normaliza espacios al inicio y al final antes de enviar usuario y API key.
- Construye el XML con `lxml.etree`.
- Usa timeout de conexión y lectura.
- No muestra la API key.
- No muestra ni almacena el token completo.
- No registra en el log el XML de solicitud, API key, token ni encabezado Authorization.
- Muestra únicamente longitudes, detección de espacios, usuario enmascarado y huellas SHA-256 parciales.
- El botón está restringido al grupo de administradores contables.

## Instalación

1. Copiar la carpeta `megaprint_fel_credentials_test` dentro del `addons_path` activo de Odoo.
2. Reiniciar el servicio de Odoo.
3. Activar modo desarrollador y actualizar la lista de aplicaciones.
4. Buscar e instalar **Megaprint FEL - Prueba segura de credenciales**.
5. Abrir **Contabilidad > Configuración > Diarios**.
6. Abrir el diario FEL y pulsar **Probar credenciales FEL**.

## Interpretación

- **Credenciales aceptadas:** Megaprint devolvió un token. El valor no se muestra ni se conserva.
- **Código 002:** Megaprint rechazó las credenciales. Se debe comparar el usuario enmascarado, longitudes, espacios y huellas parciales antes de solicitar revisión al certificador.
- **Prueba bloqueada:** el modo QA no está activo; no se efectuó ninguna llamada.
- **Timeout o error de red:** no se recibió una respuesta funcional de Megaprint.

## Dependencia

- `fel_megaprint`

## Desinstalación

La desinstalación elimina únicamente la vista y el modelo temporal del diagnóstico. No modifica las credenciales existentes ni documentos FEL.
