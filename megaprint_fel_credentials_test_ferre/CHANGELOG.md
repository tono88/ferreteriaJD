# Changelog

## 18.0.1.0.0 - 2026-06-26

- Primera versión.
- Agrega botón **Probar credenciales FEL** en el diario.
- Limita la prueba al ambiente QA.
- Construye `SolicitaTokenRequest` con `lxml.etree`.
- Normaliza espacios laterales de usuario y API key.
- Agrega timeout y manejo de errores HTTP, red y XML.
- Presenta código funcional y descripción segura.
- Muestra usuario enmascarado, longitudes, detección de espacios y huellas SHA-256 parciales.
- No muestra ni registra API key, token, Authorization o XML sensible.
- Incluye pruebas automatizadas para éxito QA, bloqueo de producción y rechazo 002.
