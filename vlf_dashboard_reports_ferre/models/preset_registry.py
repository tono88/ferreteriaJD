# -*- coding: utf-8 -*-
from odoo import _


class VlfDashboardPresetRegistry:
    """Administrador Python puro de dashboards predeterminados."""

    def __init__(self, env):
        self.env = env

    PRESET_VERSION = 2

    def _dashboard(self, technical_key, name, description, theme='blue', sequence=10):
        Dashboard = self.env['vlf.dashboard'].sudo()
        dashboard = Dashboard.search([('technical_key', '=', technical_key)], limit=1)
        if not dashboard:
            dashboard = Dashboard.search([('name', 'in', [name, name.replace(' Generales', '')])], limit=1)
        vals = {
            'name': name,
            'description': description,
            'theme': theme,
            'color_palette': 'business',
            'sequence': sequence,
            'active': True,
            'is_predefined': True,
            'technical_key': technical_key,
            'preset_version': self.PRESET_VERSION,
            'managed_by_reports': True,
            'company_ids': [(6, 0, [self.env.company.id])],
            'enable_advanced_filters': True,
        }
        if dashboard:
            dashboard.write(vals)
        else:
            dashboard = Dashboard.create(vals)
        return dashboard

    def _metric_item(self, dashboard, metric_key, name, item_type='tile', sequence=10, **kwargs):
        Item = self.env['vlf.dashboard.item'].sudo()
        item = Item.search([('dashboard_id', '=', dashboard.id), ('metric_key', '=', metric_key)], limit=1)
        vals = {
            'dashboard_id': dashboard.id,
            'name': name,
            'metric_key': metric_key,
            'managed_by_reports': True,
            'preset_version': self.PRESET_VERSION,
            'active': True,
            'sequence': sequence,
            'item_type': item_type,
            'data_source': 'odoo',
            'model_id': self.env['ir.model'].sudo().search([('model', '=', 'vlf.sales.order.fact')], limit=1).id,
            'aggregation': 'sum',
            'limit': kwargs.pop('limit', 12),
            'sort_by': 'value',
            'sort_direction': 'desc',
            'width': kwargs.pop('width', '1' if item_type == 'tile' else '2'),
            'height': kwargs.pop('height', 'medium'),
            'currency_id': self.env.company.currency_id.id if kwargs.pop('currency', False) else False,
            'number_system': kwargs.pop('number_system', 'compact'),
            'precision_digits': kwargs.pop('precision_digits', 2),
            'allow_drill_down': True,
            'show_total': True,
            'show_values': True,
            'show_legend': True,
        }
        vals.update(kwargs)
        if item:
            item.write(vals)
        else:
            item = Item.create(vals)
        return item

    def _ensure_filter(self, dashboard, key, name, field_name, value_type='many2one', sequence=10, option_values=False, placeholder=False, operator='=', alternate_field_names=False, help_text=False):
        Filter = self.env['vlf.dashboard.filter'].sudo()
        record = Filter.search([('dashboard_id', '=', dashboard.id), ('key', '=', key)], limit=1)
        vals = {
            'dashboard_id': dashboard.id,
            'active': True,
            'sequence': sequence,
            'name': name,
            'key': key,
            'field_name': field_name,
            'value_type': value_type,
            'operator': operator,
            'alternate_field_names': alternate_field_names or False,
            'help_text': help_text or False,
            'placeholder': placeholder or (_('Nombre o ID') if value_type == 'char' else _('Seleccione una opción')),
            'option_values': option_values or False,
        }
        if record:
            record.write(vals)
        else:
            Filter.create(vals)

    def _selection_options(self, records):
        lines = []
        for record in records:
            label = (record.display_name or str(record.id)).replace('\n', ' ')
            lines.append(f'{record.id}:{label}')
        return '\n'.join(lines)

    def _common_filters(self, dashboard, include_channel=True):
        warehouses = self.env['stock.warehouse'].sudo().search([
            ('company_id', '=', self.env.company.id),
        ], order='name')
        pos_configs = self.env['pos.config'].sudo().search([
            ('company_id', '=', self.env.company.id),
        ], order='name')
        users = self.env['res.users'].sudo().search([
            ('active', '=', True),
            ('company_ids', 'in', [self.env.company.id]),
        ], order='name', limit=200)
        self._ensure_filter(
            dashboard, 'sucursal', _('Sucursal / Almacén'), 'warehouse_id',
            value_type='selection', sequence=10,
            option_values=self._selection_options(warehouses),
            alternate_field_names='order_id.config_id.warehouse_id\nconfig_id.warehouse_id\npos_order_id.config_id.warehouse_id\norder_id.warehouse_id',
        )
        self._ensure_filter(
            dashboard, 'pos', _('Punto de Venta'), 'pos_config_id',
            value_type='selection', sequence=20,
            option_values=self._selection_options(pos_configs),
            alternate_field_names='config_id\norder_id.config_id\npos_order_id.config_id',
        )
        self._ensure_filter(
            dashboard, 'cliente', _('Cliente'), 'partner_id',
            value_type='char', sequence=30, operator='ilike',
            alternate_field_names='order_id.partner_id\nmove_id.partner_id\npos_order_id.partner_id',
            placeholder=_('Nombre del cliente'),
        )
        self._ensure_filter(
            dashboard, 'vendedor', _('Vendedor / Cajero'), 'user_id',
            value_type='selection', sequence=40,
            option_values=self._selection_options(users),
            alternate_field_names='invoice_user_id\norder_id.user_id\npos_order_id.user_id',
        )
        if include_channel:
            self._ensure_filter(
                dashboard, 'canal', _('Canal'), 'channel', value_type='selection', sequence=50,
                option_values='sale:Ventas\npos:Punto de Venta',
            )

    def apply_presets(self):
        sales = self._dashboard(
            'reports.sales.general',
            'Ventas Generales',
            'Venta operativa consolidada de POS y Ventas administrativas, sin duplicar facturas.',
            theme='green',
            sequence=20,
        )
        pos = self._dashboard(
            'reports.sales.pos',
            'Punto de Venta',
            'Indicadores exclusivos de cajas, sesiones, métodos de pago y operación POS.',
            theme='orange',
            sequence=30,
        )
        executive = self._dashboard(
            'reports.executive',
            'Ejecutivo Gerencial',
            'Resumen gerencial con ventas operativas separadas de la facturación financiera.',
            theme='blue',
            sequence=10,
        )

        # Se desactivan únicamente los presets débiles conocidos del módulo base.
        old_sales_names = ['Ventas por mes', 'Ventas por vendedor', 'Top clientes', 'Embudo por estado', 'Pedidos recientes', 'Top productos POS']
        old_pos_names = ['Ventas POS por día', 'Ventas por cajero', 'Órdenes por estado', 'Sesiones POS', 'Órdenes POS recientes', 'Top productos POS']
        old_exec_names = ['Ventas confirmadas', 'Facturación clientes', 'Ventas POS', 'Ventas mensuales']
        self.env['vlf.dashboard.item'].sudo().search([
            ('dashboard_id', '=', sales.id), ('metric_key', '=', False), ('name', 'in', old_sales_names)
        ]).write({'active': False})
        self.env['vlf.dashboard.item'].sudo().search([
            ('dashboard_id', '=', pos.id), ('metric_key', '=', False), ('name', 'in', old_pos_names)
        ]).write({'active': False})
        self.env['vlf.dashboard.item'].sudo().search([
            ('dashboard_id', '=', executive.id), ('metric_key', '=', False), ('name', 'in', old_exec_names)
        ]).write({'active': False})

        self._common_filters(sales, include_channel=True)
        self._common_filters(pos, include_channel=False)
        self._common_filters(executive, include_channel=True)

        sales_items = [
            ('sales.total_net', 'Venta neta total', 'tile', 10, {'currency': True, 'icon': 'fa-line-chart'}),
            ('sales.pos_net', 'Ventas POS', 'tile', 20, {'currency': True, 'icon': 'fa-shopping-cart'}),
            ('sales.admin_net', 'Ventas administrativas', 'tile', 30, {'currency': True, 'icon': 'fa-file-text-o'}),
            ('sales.refunds', 'Devoluciones', 'tile', 40, {'currency': True, 'icon': 'fa-undo'}),
            ('sales.order_count', 'Cantidad de ventas', 'tile', 50, {'icon': 'fa-list-ol', 'precision_digits': 0}),
            ('sales.average_ticket', 'Ticket promedio', 'tile', 60, {'currency': True, 'icon': 'fa-calculator'}),
            ('sales.by_month', 'Ventas por mes', 'area', 70, {'currency': True, 'width': '2', 'icon': 'fa-calendar'}),
            ('sales.by_warehouse', 'Ventas por sucursal', 'bar', 80, {'currency': True, 'width': '2', 'icon': 'fa-building'}),
            ('sales.by_channel', 'Ventas por canal', 'doughnut', 90, {'currency': True, 'width': '2', 'icon': 'fa-random'}),
            ('sales.top_customers', 'Top clientes', 'horizontal_bar', 100, {'currency': True, 'width': '2', 'icon': 'fa-users'}),
            ('sales.top_products', 'Top productos', 'horizontal_bar', 110, {'width': '2', 'icon': 'fa-cubes'}),
            ('sales.recent', 'Ventas recientes', 'list', 120, {'width': '4', 'limit': 20, 'icon': 'fa-clock-o'}),
        ]
        for key, name, item_type, sequence, values in sales_items:
            self._metric_item(sales, key, name, item_type, sequence, **values)

        pos_items = [
            ('sales.pos_net', 'Ventas POS netas', 'tile', 10, {'currency': True, 'icon': 'fa-shopping-cart'}),
            ('pos.order_count', 'Órdenes POS', 'tile', 20, {'icon': 'fa-list-ol', 'precision_digits': 0}),
            ('pos.average_ticket', 'Ticket promedio POS', 'tile', 30, {'currency': True, 'icon': 'fa-calculator'}),
            ('pos.refunds', 'Devoluciones POS', 'tile', 40, {'currency': True, 'icon': 'fa-undo'}),
            ('pos.discount_total', 'Descuentos POS', 'tile', 50, {'currency': True, 'icon': 'fa-percent'}),
            ('pos.by_day', 'Ventas POS por día', 'area', 60, {'currency': True, 'width': '2', 'icon': 'fa-calendar'}),
            ('pos.by_config', 'Ventas por punto de venta', 'bar', 70, {'currency': True, 'width': '2', 'icon': 'fa-desktop'}),
            ('pos.by_warehouse', 'Ventas POS por sucursal', 'bar', 80, {'currency': True, 'width': '2', 'icon': 'fa-building'}),
            ('pos.by_cashier', 'Ventas por cajero', 'bar', 90, {'currency': True, 'width': '2', 'icon': 'fa-user'}),
            ('pos.by_payment_method', 'Métodos de pago', 'doughnut', 100, {'currency': True, 'width': '2', 'icon': 'fa-credit-card'}),
            ('pos.invoicing_status', 'Facturadas y no facturadas', 'doughnut', 110, {'currency': True, 'width': '2', 'icon': 'fa-file-text-o'}),
            ('pos.sessions_state', 'Sesiones POS', 'pie', 120, {'width': '2', 'icon': 'fa-play-circle'}),
            ('pos.top_customers', 'Top clientes POS', 'horizontal_bar', 130, {'currency': True, 'width': '2', 'icon': 'fa-users'}),
            ('pos.top_products', 'Top productos POS', 'horizontal_bar', 140, {'width': '2', 'icon': 'fa-cubes'}),
            ('pos.recent', 'Órdenes POS recientes', 'list', 150, {'width': '4', 'limit': 20, 'icon': 'fa-clock-o'}),
        ]
        for key, name, item_type, sequence, values in pos_items:
            self._metric_item(pos, key, name, item_type, sequence, **values)

        executive_items = [
            ('sales.total_net', 'Venta operativa neta', 'tile', 10, {'currency': True, 'icon': 'fa-line-chart'}),
            ('sales.pos_net', 'Venta POS', 'tile', 20, {'currency': True, 'icon': 'fa-shopping-cart'}),
            ('sales.admin_net', 'Venta administrativa', 'tile', 30, {'currency': True, 'icon': 'fa-file-text-o'}),
            ('billing.issued', 'Facturación emitida', 'tile', 40, {'currency': True, 'icon': 'fa-money'}),
            ('sales.refunds', 'Devoluciones operativas', 'tile', 50, {'currency': True, 'icon': 'fa-undo'}),
            ('sales.by_month', 'Venta operativa mensual', 'area', 60, {'currency': True, 'width': '2', 'icon': 'fa-calendar'}),
            ('sales.by_warehouse', 'Venta por sucursal', 'bar', 70, {'currency': True, 'width': '2', 'icon': 'fa-building'}),
            ('sales.by_channel', 'Participación por canal', 'doughnut', 80, {'currency': True, 'width': '2', 'icon': 'fa-random'}),
            ('sales.top_customers', 'Top clientes', 'horizontal_bar', 90, {'currency': True, 'width': '2', 'icon': 'fa-users'}),
            ('sales.top_products', 'Top productos', 'horizontal_bar', 100, {'width': '2', 'icon': 'fa-cubes'}),
        ]
        for key, name, item_type, sequence, values in executive_items:
            self._metric_item(executive, key, name, item_type, sequence, **values)

        return {
            'dashboards': 3,
            'version': self.PRESET_VERSION,
        }
