# Tecnodyne Dashboard Pro para Odoo 18

Módulo original de dashboards operativos para Odoo 18.

Incluye:

- Constructor visual drag and drop.
- Gráficas tipo tile, línea, lista, barras, barras horizontales, to-do, polar area, pie, doughnut, flower, funnel, radial, bullet, scatter, radar, map y area.
- Dashboards múltiples.
- Auto refresh / actualización en vivo.
- Filtros por fecha, compañía y filtros personalizados.
- Exportación JSON / CSV / impresión PDF desde navegador.
- Importación JSON de dashboards.
- Datasets desde Excel/CSV básico.
- Presets comerciales: top productos vendidos, productos menos vendidos, top clientes, POS, facturación e inventario.
- Ayuda integrada con ejemplos de configuración.

No incluye funciones de IA. Esa parte queda preparada para una versión posterior.

## Filtros personalizados

Desde el formulario del dashboard, pestaña **Filtros personalizados**, se pueden crear filtros que aparecen en la parte superior del dashboard.

Campos importantes:

- **Nombre**: texto visible para el usuario.
- **Clave**: identificador técnico, por ejemplo `cliente`, `producto`, `vendedor`.
- **Campo técnico**: campo Odoo a filtrar, por ejemplo `partner_id`, `user_id`, `state`, `product_id`, `order_id.partner_id`.
- **Tipo**: texto, número, registro por ID, fecha, sí/no o selección manual.
- **Operador**: igual, contiene, mayor que, está en lista, etc.

Ejemplos:

- Cliente en pedidos de venta: `partner_id`.
- Cliente desde líneas de venta: `order_id.partner_id`.
- Producto desde líneas de venta: `product_id`.
- Vendedor en ventas: `user_id`.
- Estado en ventas: `state`.
- Cliente desde líneas de factura: `move_id.partner_id`.

Para selección manual, usar una opción por línea:

```text
draft:Cotización
sale:Venta confirmada
done:Bloqueado
cancel:Cancelado
```

## Instalación

1. Copiar la carpeta `vlf_dashboard_pro` en la ruta de addons de Odoo.
2. Reiniciar Odoo.
3. Actualizar lista de aplicaciones.
4. Buscar **Tecnodyne Dashboard Pro**.
5. Instalar o actualizar.
6. Ejecutar Ctrl + F5 en el navegador para recargar assets.


## 18.0.2.3.0

- Corrige el botón **Ver datos** agregando la propiedad `views` requerida por `doAction` en Odoo 18.
- Agrega **Filtros sugeridos** desde el dashboard. Los filtros se proponen según los modelos/campos usados en las tarjetas actuales.
- Permite agregar filtros sugeridos con un clic sin entrar primero al formulario de configuración.
- Agrega campos alternos por filtro, por ejemplo `partner_id`, `order_id.partner_id` y `move_id.partner_id`, para que un mismo filtro funcione en varios modelos del mismo dashboard.
- Renombra el menú visible a **Tecnodyne Dashboards**.
