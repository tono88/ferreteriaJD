# Datos de prueba

Al instalar con datos de demostración se crean:

- `Demo Sucursal Solicitante` con código `DSS`.
- `Demo Sucursal Suministradora` con código `DSP`.
- `Producto demo para traslado`.

No se crea inventario automáticamente para evitar alterar existencias en una base con demos mezclados. Para una prueba manual:

1. Realizar un ajuste de inventario de 20 unidades del producto demo en la ubicación principal de `DSP`.
2. Crear tres usuarios de prueba o reutilizar usuarios existentes:
   - solicitante autorizado en `DSS`;
   - aprobador autorizado en `DSP`;
   - receptor autorizado en `DSS`.
3. Crear una solicitud por 8 unidades desde `DSS`, suministrada por `DSP`.
4. Probar primero aprobación total por 8.
5. Repetir con otra solicitud aprobando 5 de 8 y recibiendo 3 de 5 para generar una incidencia automática por 2.

Los datos demo solo se cargan cuando la base está habilitada para demostración.
