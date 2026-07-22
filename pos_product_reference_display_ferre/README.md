# POS Product Reference Display Ferre

Módulo mínimo para Odoo 18 Community que muestra los productos del Punto de Venta con el formato:

```text
[default_code] Nombre del producto
```

Ejemplo:

```text
[ABR-001] ABRAZADERA CON RANURA 1-1/2"
```

## Alcance

- Muestra primero la referencia interna (`product.product.default_code`).
- Conserva después el nombre del producto.
- Los productos sin referencia muestran únicamente su nombre.
- Respeta carga completa y carga limitada de productos.
- No modifica JavaScript, creación de órdenes, clientes, pagos, precios ni inventario.
- La búsqueda estándar de Odoo 18 continúa funcionando por nombre, referencia interna y código de barras.

## Instalación

1. Cerrar las sesiones o pestañas abiertas del POS.
2. Copiar la carpeta `pos_product_reference_display_ferre` al `addons_path`.
3. Reiniciar Odoo.
4. Actualizar la lista de aplicaciones.
5. Instalar `POS Product Reference Display Ferre`.
6. Abrir nuevamente el POS con una sesión nueva o recargarlo completamente.

## Licencia

AGPL-3. La implementación sigue el enfoque del módulo OCA
`pos_product_display_default_code` para Odoo 18.
