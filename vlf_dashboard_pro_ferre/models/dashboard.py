# -*- coding: utf-8 -*-
import json
import logging
import re
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class VlfDashboard(models.Model):
    _name = 'vlf.dashboard'
    _description = 'Tecnodyne Dashboard'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(index=True, copy=False)
    description = fields.Text()
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    item_ids = fields.One2many('vlf.dashboard.item', 'dashboard_id', string='Items')
    todo_ids = fields.One2many('vlf.dashboard.todo', 'dashboard_id', string='To-do')
    filter_ids = fields.One2many('vlf.dashboard.filter', 'dashboard_id', string='Filtros personalizados')

    layout_mode = fields.Selection([
        ('grid', 'Grid flexible'),
        ('compact', 'Compacto'),
        ('list', 'Lista'),
    ], default='grid', required=True)
    theme = fields.Selection([
        ('light', 'Claro'),
        ('dark', 'Oscuro'),
        ('blue', 'Azul'),
        ('green', 'Verde'),
        ('orange', 'Naranja'),
        ('purple', 'Morado'),
    ], default='light', required=True)
    color_palette = fields.Selection([
        ('classic', 'Clásica'),
        ('business', 'Empresarial'),
        ('pastel', 'Pastel'),
        ('contrast', 'Contraste'),
        ('mono', 'Monocromática'),
    ], default='business')

    auto_refresh = fields.Boolean(string='Auto refrescar')
    auto_refresh_seconds = fields.Integer(default=60)
    enable_realtime = fields.Boolean(string='Streaming / actualización en vivo')
    enable_advanced_filters = fields.Boolean(default=True)
    allow_export = fields.Boolean(default=True)
    allow_import = fields.Boolean(default=True)
    allow_instant_edit = fields.Boolean(default=True)
    is_predefined = fields.Boolean(string='Dashboard predefinido', copy=False)

    company_ids = fields.Many2many('res.company', string='Compañías permitidas')
    group_ids = fields.Many2many('res.groups', string='Grupos con acceso')
    owner_id = fields.Many2one('res.users', default=lambda self: self.env.user)

    item_count = fields.Integer(compute='_compute_item_count')

    @api.depends('item_ids')
    def _compute_item_count(self):
        for dashboard in self:
            dashboard.item_count = len(dashboard.item_ids.filtered('active'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code'):
                vals['code'] = self.env['ir.sequence'].next_by_code('vlf.dashboard') or False
        return super().create(vals_list)

    def _user_can_access(self):
        self.ensure_one()
        user = self.env.user
        if user.has_group('vlf_dashboard_pro_ferre.group_vlf_dashboard_manager'):
            return True
        if self.company_ids and user.company_id not in self.company_ids:
            return False
        if self.group_ids and not (self.group_ids & user.groups_id):
            return False
        return True

    @api.model
    def get_dashboard_catalog(self):
        dashboards = self.search([('active', '=', True)])
        result = []
        for dashboard in dashboards:
            if dashboard._user_can_access():
                result.append({
                    'id': dashboard.id,
                    'name': dashboard.name,
                    'theme': dashboard.theme,
                    'layout_mode': dashboard.layout_mode,
                    'is_predefined': dashboard.is_predefined,
                    'auto_refresh': dashboard.auto_refresh or dashboard.enable_realtime,
                    'auto_refresh_seconds': max(dashboard.auto_refresh_seconds or 60, 10),
                })
        return result


    def _get_custom_filters_payload(self):
        self.ensure_one()
        filters = []
        for record in self.filter_ids.filtered('active').sorted(lambda f: f.sequence):
            filters.append({
                'id': record.id,
                'name': record.name,
                'key': record.key,
                'field_name': record.field_name,
                'alternate_field_names': record.alternate_field_names or '',
                'value_type': record.value_type,
                'operator': record.operator,
                'placeholder': record.placeholder or '',
                'default_value': record.default_value or '',
                'help_text': record.help_text or '',
                'options': record._get_options_payload(),
            })
        return filters

    @api.model
    def get_dashboard_payload(self, dashboard_id=False, filters=None):
        filters = filters or {}
        dashboard = self.browse(int(dashboard_id)) if dashboard_id else self.search([('active', '=', True)], limit=1)
        if not dashboard:
            return {
                'dashboard': False,
                'items': [],
                'catalog': [],
                'filters': filters,
            }
        dashboard.ensure_one()
        if not dashboard._user_can_access():
            raise UserError(_('No tienes acceso a este dashboard.'))

        items = []
        for item in dashboard.item_ids.filtered('active').sorted(lambda i: i.sequence):
            try:
                items.append(item.get_payload(filters=filters))
            except Exception as exc:  # keep dashboard useful even if one card fails
                _logger.exception('Error rendering dashboard item %s', item.display_name)
                items.append(item.get_error_payload(str(exc)))

        return {
            'dashboard': {
                'id': dashboard.id,
                'name': dashboard.name,
                'description': dashboard.description or '',
                'theme': dashboard.theme,
                'layout_mode': dashboard.layout_mode,
                'auto_refresh': dashboard.auto_refresh or dashboard.enable_realtime,
                'auto_refresh_seconds': max(dashboard.auto_refresh_seconds or 60, 10),
                'enable_advanced_filters': dashboard.enable_advanced_filters,
                'allow_export': dashboard.allow_export,
                'allow_import': dashboard.allow_import,
                'allow_instant_edit': dashboard.allow_instant_edit,
                'color_palette': dashboard.color_palette,
                'company_ids': dashboard.company_ids.ids,
                'custom_filters': dashboard._get_custom_filters_payload(),
                'suggested_filters': dashboard._get_suggested_filters_payload(),
            },
            'items': items,
            'catalog': self.get_dashboard_catalog(),
            'filters': filters,
            'context': {
                'uid': self.env.uid,
                'user_name': self.env.user.name,
                'company_id': self.env.company.id,
                'company_name': self.env.company.name,
                'lang': self.env.lang,
            },
        }


    def _dashboard_model_names(self):
        self.ensure_one()
        return set(self.item_ids.filtered(lambda item: item.active and item.model_id).mapped('model_id.model'))

    def _suggested_filter_definitions(self):
        """Central catalog of quick filters that can be added from the dashboard UI.

        field_name is the preferred field. alternate_field_names are tried when an item uses
        another model, for example sale.order.line uses order_id.partner_id instead of partner_id.
        """
        return [
            {
                'key': 'cliente',
                'name': _('Cliente'),
                'field_name': 'partner_id',
                'alternate_field_names': 'order_id.partner_id\nmove_id.partner_id',
                'value_type': 'char',
                'operator': 'ilike',
                'placeholder': _('Nombre del cliente'),
                'help_text': _('Filtra clientes en ventas, POS, facturación y líneas cuando el modelo lo permite.'),
                'icon': 'fa-user',
            },
            {
                'key': 'producto',
                'name': _('Producto'),
                'field_name': 'product_id',
                'alternate_field_names': 'product_tmpl_id',
                'value_type': 'char',
                'operator': 'ilike',
                'placeholder': _('Nombre o código del producto'),
                'help_text': _('Filtra productos en líneas de venta, POS, factura e inventario.'),
                'icon': 'fa-cube',
            },
            {
                'key': 'vendedor',
                'name': _('Vendedor / Usuario'),
                'field_name': 'user_id',
                'alternate_field_names': 'order_id.user_id\ninvoice_user_id\nmove_id.invoice_user_id',
                'value_type': 'char',
                'operator': 'ilike',
                'placeholder': _('Nombre del vendedor o usuario'),
                'help_text': _('Filtra por vendedor o usuario responsable según el modelo de cada tarjeta.'),
                'icon': 'fa-id-badge',
            },
            {
                'key': 'estado_venta',
                'name': _('Estado de venta'),
                'field_name': 'state',
                'alternate_field_names': 'order_id.state',
                'value_type': 'selection',
                'operator': '=',
                'placeholder': '',
                'option_values': 'draft:Cotización\nsent:Cotización enviada\nsale:Venta confirmada\ndone:Bloqueado\ncancel:Cancelado',
                'help_text': _('Útil para dashboards basados en pedidos de venta o líneas de pedido.'),
                'icon': 'fa-tags',
            },
            {
                'key': 'estado_pos',
                'name': _('Estado POS'),
                'field_name': 'state',
                'alternate_field_names': 'order_id.state',
                'value_type': 'selection',
                'operator': '=',
                'placeholder': '',
                'option_values': 'draft:Nuevo\npaid:Pagado\ndone:Publicado\ninvoiced:Facturado\ncancel:Cancelado',
                'help_text': _('Útil para dashboards de Punto de Venta.'),
                'icon': 'fa-shopping-cart',
            },
            {
                'key': 'estado_pago',
                'name': _('Estado de pago'),
                'field_name': 'payment_state',
                'alternate_field_names': 'move_id.payment_state',
                'value_type': 'selection',
                'operator': '=',
                'placeholder': '',
                'option_values': 'not_paid:No pagado\nin_payment:En proceso de pago\npaid:Pagado\npartial:Parcial\nreversed:Revertido\nblocked:Bloqueado\ninvoicing_legacy:Sistema anterior',
                'help_text': _('Filtra facturas y asientos por estado de pago cuando existe el campo.'),
                'icon': 'fa-credit-card',
            },
            {
                'key': 'tipo_documento',
                'name': _('Tipo de documento'),
                'field_name': 'move_type',
                'alternate_field_names': 'move_id.move_type',
                'value_type': 'selection',
                'operator': '=',
                'placeholder': '',
                'option_values': 'out_invoice:Factura de cliente\nout_refund:Nota de crédito cliente\nin_invoice:Factura de proveedor\nin_refund:Nota de crédito proveedor\nentry:Asiento contable',
                'help_text': _('Filtra documentos contables por tipo.'),
                'icon': 'fa-file-text-o',
            },
            {
                'key': 'categoria_producto',
                'name': _('Categoría de producto'),
                'field_name': 'product_id.categ_id',
                'alternate_field_names': 'product_tmpl_id.categ_id',
                'value_type': 'char',
                'operator': 'ilike',
                'placeholder': _('Nombre de categoría'),
                'help_text': _('Filtra por categoría del producto usando relación product_id.categ_id.'),
                'icon': 'fa-folder-open',
            },
            {
                'key': 'ubicacion',
                'name': _('Ubicación de inventario'),
                'field_name': 'location_id',
                'alternate_field_names': '',
                'value_type': 'char',
                'operator': 'ilike',
                'placeholder': _('Nombre de ubicación'),
                'help_text': _('Filtra tarjetas de inventario por ubicación.'),
                'icon': 'fa-map-marker',
            },
            {
                'key': 'compania_texto',
                'name': _('Compañía'),
                'field_name': 'company_id',
                'alternate_field_names': 'order_id.company_id\nmove_id.company_id',
                'value_type': 'char',
                'operator': 'ilike',
                'placeholder': _('Nombre de compañía'),
                'help_text': _('Filtro por nombre de compañía. También puedes usar el filtro global por ID de compañía.'),
                'icon': 'fa-building',
            },
        ]

    def _field_candidate_is_available(self, model_name, candidate):
        if not model_name or not candidate:
            return False
        try:
            model_obj = self.env[model_name]
        except KeyError:
            return False
        first = candidate.split('.')[0]
        return first in model_obj._fields

    def _suggestion_matches_dashboard(self, definition, model_names):
        candidates = [definition.get('field_name')] + [line.strip() for line in (definition.get('alternate_field_names') or '').replace(',', '\n').replace(';', '\n').splitlines() if line.strip()]
        for model_name in model_names:
            for candidate in candidates:
                if self._field_candidate_is_available(model_name, candidate):
                    return True
        return False

    def _get_suggested_filters_payload(self):
        self.ensure_one()
        model_names = self._dashboard_model_names()
        existing_keys = set(self.filter_ids.mapped('key'))
        suggestions = []
        for definition in self._suggested_filter_definitions():
            if definition['key'] in existing_keys:
                continue
            if not model_names or self._suggestion_matches_dashboard(definition, model_names):
                values = dict(definition)
                values['model_count'] = len(model_names)
                suggestions.append(values)
        return suggestions

    @api.model
    def add_filter_from_suggestion(self, dashboard_id, key):
        dashboard = self.browse(int(dashboard_id))
        dashboard.ensure_one()
        if not dashboard._user_can_access():
            raise UserError(_('No tienes acceso a este dashboard.'))
        if not self.env.user.has_group('vlf_dashboard_pro_ferre.group_vlf_dashboard_manager'):
            raise UserError(_('Solo un usuario administrador del dashboard puede agregar filtros.'))
        definitions = {definition['key']: definition for definition in dashboard._suggested_filter_definitions()}
        if key not in definitions:
            raise UserError(_('Filtro sugerido no reconocido: %s') % key)
        existing = dashboard.filter_ids.filtered(lambda f: f.key == key)
        if existing:
            return {'id': existing[0].id, 'name': existing[0].name, 'already_exists': True}
        definition = dict(definitions[key])
        model_names = dashboard._dashboard_model_names()
        if model_names and not dashboard._suggestion_matches_dashboard(definition, model_names):
            raise UserError(_('Este filtro no aplica a las tarjetas actuales del dashboard.'))
        Filter = self.env['vlf.dashboard.filter'].sudo()
        next_sequence = (max(dashboard.filter_ids.mapped('sequence') or [0]) or 0) + 10
        record = Filter.create({
            'dashboard_id': dashboard.id,
            'active': True,
            'sequence': next_sequence,
            'name': definition.get('name'),
            'key': definition.get('key'),
            'field_name': definition.get('field_name'),
            'alternate_field_names': definition.get('alternate_field_names'),
            'value_type': definition.get('value_type') or 'char',
            'operator': definition.get('operator') or '=',
            'placeholder': definition.get('placeholder'),
            'option_values': definition.get('option_values'),
            'help_text': definition.get('help_text'),
        })
        return {'id': record.id, 'name': record.name, 'already_exists': False}



    @api.model
    def get_builder_catalog(self):
        """Catalog used by the visual builder/drag and drop panel."""
        chart_types = [
            {'key': 'tile', 'name': 'Tile / KPI', 'icon': 'fa-square'},
            {'key': 'line', 'name': 'Line Chart', 'icon': 'fa-line-chart'},
            {'key': 'list', 'name': 'List View', 'icon': 'fa-list'},
            {'key': 'bar', 'name': 'Bar Chart', 'icon': 'fa-bar-chart'},
            {'key': 'horizontal_bar', 'name': 'Horizontal Bar', 'icon': 'fa-align-left'},
            {'key': 'todo', 'name': 'To-do Item', 'icon': 'fa-check-square-o'},
            {'key': 'polar_area', 'name': 'Polar Area', 'icon': 'fa-pie-chart'},
            {'key': 'pie', 'name': 'Pie Chart', 'icon': 'fa-pie-chart'},
            {'key': 'doughnut', 'name': 'Doughnut Chart', 'icon': 'fa-circle-o'},
            {'key': 'flower', 'name': 'Flower Chart', 'icon': 'fa-asterisk'},
            {'key': 'funnel', 'name': 'Funnel Chart', 'icon': 'fa-filter'},
            {'key': 'radial', 'name': 'Radial Chart', 'icon': 'fa-dot-circle-o'},
            {'key': 'bullet', 'name': 'Bullet Chart', 'icon': 'fa-bullseye'},
            {'key': 'scatter', 'name': 'Scatter Chart', 'icon': 'fa-random'},
            {'key': 'radar', 'name': 'Radar Chart', 'icon': 'fa-location-arrow'},
            {'key': 'map', 'name': 'Map View', 'icon': 'fa-map-marker'},
            {'key': 'area', 'name': 'Area Chart', 'icon': 'fa-area-chart'},
        ]
        presets = [
            {'key': 'top_products_sold', 'name': 'Top productos vendidos', 'description': 'Ventas confirmadas por cantidad vendida', 'icon': 'fa-cubes'},
            {'key': 'least_products_sold', 'name': 'Productos menos vendidos', 'description': 'Productos con menor cantidad vendida', 'icon': 'fa-sort-amount-asc'},
            {'key': 'top_customers_amount', 'name': 'Top clientes por compra', 'description': 'Clientes con mayor monto comprado', 'icon': 'fa-users'},
            {'key': 'top_customers_count', 'name': 'Clientes con más pedidos', 'description': 'Clientes con más órdenes confirmadas', 'icon': 'fa-repeat'},
            {'key': 'top_pos_products', 'name': 'Top productos POS', 'description': 'Productos más vendidos en punto de venta', 'icon': 'fa-shopping-cart'},
            {'key': 'top_invoiced_products', 'name': 'Top productos facturados', 'description': 'Productos por cantidad facturada', 'icon': 'fa-file-text-o'},
            {'key': 'customers_by_invoicing', 'name': 'Top clientes facturados', 'description': 'Clientes por monto facturado publicado', 'icon': 'fa-money'},
            {'key': 'slow_stock', 'name': 'Inventario con menor existencia', 'description': 'Productos con menor cantidad disponible', 'icon': 'fa-archive'},
        ]
        return {'chart_types': chart_types, 'presets': presets}

    def _builder_find_model(self, model_name):
        model = self.env['ir.model'].sudo().search([('model', '=', model_name)], limit=1)
        if not model:
            raise UserError(_('No se encontró el modelo %s. Verifica que el módulo correspondiente esté instalado.') % model_name)
        return model

    def _builder_find_field(self, model, field_name, required=False):
        if not model or not field_name:
            return False
        field = self.env['ir.model.fields'].sudo().search([('model_id', '=', model.id), ('name', '=', field_name)], limit=1)
        if required and not field:
            raise UserError(_('No se encontró el campo %s en el modelo %s.') % (field_name, model.model))
        return field

    @api.model
    def create_item_from_builder(self, dashboard_id, builder_payload):
        """Create a dashboard item from a dragged chart type or business preset."""
        dashboard = self.browse(int(dashboard_id))
        dashboard.ensure_one()
        if not dashboard._user_can_access():
            raise UserError(_('No tienes acceso a este dashboard.'))
        if not self.env.user.has_group('vlf_dashboard_pro_ferre.group_vlf_dashboard_manager'):
            raise UserError(_('Solo un usuario administrador del dashboard puede agregar elementos.'))
        if not dashboard.allow_instant_edit:
            raise UserError(_('La edición instantánea está desactivada para este dashboard.'))

        builder_payload = builder_payload or {}
        kind = builder_payload.get('kind') or 'type'
        key = builder_payload.get('key') or 'tile'
        item_model = self.env['vlf.dashboard.item'].sudo()
        next_sequence = (max(dashboard.item_ids.mapped('sequence') or [0]) or 0) + 10
        currency = self.env.company.currency_id

        def field(model, name, required=False):
            return self._builder_find_field(model, name, required=required)

        def base_vals(name, item_type, icon='fa-bar-chart', width='2', height='medium'):
            return {
                'dashboard_id': dashboard.id,
                'name': name,
                'item_type': item_type,
                'sequence': next_sequence,
                'width': width,
                'height': height,
                'aggregation': 'sum',
                'limit': 10,
                'sort_by': 'value',
                'sort_direction': 'desc',
                'number_system': 'compact',
                'precision_digits': 2,
                'icon': icon,
                'color_palette': 'inherit',
                'show_values': True,
                'show_legend': True,
                'show_total': True,
                'allow_drill_down': True,
            }

        def set_odoo(vals, model_name, measure=False, groupby=False, date_field=False, domain='[]', use_currency=False, aggregation='sum'):
            model = self._builder_find_model(model_name)
            vals.update({
                'data_source': 'odoo',
                'model_id': model.id,
                'domain': domain,
                'aggregation': aggregation,
                'measure_field_id': field(model, measure).id if measure and field(model, measure) else False,
                'groupby_field_id': field(model, groupby).id if groupby and field(model, groupby) else False,
                'date_field_id': field(model, date_field).id if date_field and field(model, date_field) else False,
                'currency_id': currency.id if use_currency and currency else False,
            })
            return vals

        date_domain_sale_line = "[('order_id.state','in',['sale','done']),('product_id','!=',False),('product_uom_qty','>',0)] + ([('order_id.date_order','>=', DATE_FROM)] if DATE_FROM else []) + ([('order_id.date_order','<=', DATE_TO)] if DATE_TO else [])"
        date_domain_pos_line = "[('order_id.state','in',['paid','done','invoiced']),('product_id','!=',False),('qty','>',0)] + ([('order_id.date_order','>=', DATE_FROM)] if DATE_FROM else []) + ([('order_id.date_order','<=', DATE_TO)] if DATE_TO else [])"
        date_domain_invoice_line = "[('move_id.move_type','in',['out_invoice','out_refund']),('parent_state','=','posted'),('product_id','!=',False),('quantity','>',0)] + ([('move_id.invoice_date','>=', DATE_FROM)] if DATE_FROM else []) + ([('move_id.invoice_date','<=', DATE_TO)] if DATE_TO else [])"

        presets = {
            'top_products_sold': lambda: set_odoo(base_vals('Top productos vendidos', 'horizontal_bar', 'fa-cubes'), 'sale.order.line', 'product_uom_qty', 'product_id', False, date_domain_sale_line),
            'least_products_sold': lambda: dict(set_odoo(base_vals('Productos menos vendidos', 'horizontal_bar', 'fa-sort-amount-asc'), 'sale.order.line', 'product_uom_qty', 'product_id', False, date_domain_sale_line), sort_direction='asc'),
            'top_customers_amount': lambda: set_odoo(base_vals('Top clientes por monto comprado', 'horizontal_bar', 'fa-users'), 'sale.order', 'amount_total', 'partner_id', 'date_order', "[('state','in',['sale','done'])]", use_currency=True),
            'top_customers_count': lambda: set_odoo(dict(base_vals('Clientes con más pedidos', 'bar', 'fa-repeat'), aggregation='count'), 'sale.order', False, 'partner_id', 'date_order', "[('state','in',['sale','done'])]", aggregation='count'),
            'top_pos_products': lambda: set_odoo(base_vals('Top productos POS', 'horizontal_bar', 'fa-shopping-cart'), 'pos.order.line', 'qty', 'product_id', False, date_domain_pos_line),
            'top_invoiced_products': lambda: set_odoo(base_vals('Top productos facturados', 'horizontal_bar', 'fa-file-text-o'), 'account.move.line', 'quantity', 'product_id', False, date_domain_invoice_line),
            'customers_by_invoicing': lambda: set_odoo(base_vals('Top clientes facturados', 'horizontal_bar', 'fa-money'), 'account.move', 'amount_total_signed', 'partner_id', 'invoice_date', "[('move_type','=','out_invoice'),('state','=','posted')]", use_currency=True),
            'slow_stock': lambda: set_odoo(dict(base_vals('Inventario con menor existencia', 'horizontal_bar', 'fa-archive'), sort_direction='asc'), 'stock.quant', 'quantity', 'product_id', False, "[('quantity','>',0)]"),
        }

        # Fix a typo-prone width expression through explicit override after creation of the preset dict.
        if kind == 'preset':
            if key not in presets:
                raise UserError(_('Preset no reconocido: %s') % key)
            vals = presets[key]()
        else:
            valid_types = [item['key'] for item in self.get_builder_catalog()['chart_types']]
            if key not in valid_types:
                raise UserError(_('Tipo de gráfica no reconocido: %s') % key)
            default_name = dict((item['key'], item['name']) for item in self.get_builder_catalog()['chart_types']).get(key, _('Nuevo item'))
            vals = base_vals(default_name, key, width='1' if key == 'tile' else '2')
            if key == 'todo':
                vals.update({'data_source': 'odoo', 'model_id': False, 'aggregation': 'count', 'width': '2'})
            elif key == 'map':
                vals = set_odoo(vals, 'res.partner', False, False, False, "[('partner_latitude','!=',False),('partner_longitude','!=',False)]", aggregation='count')
            elif key == 'list':
                vals = set_odoo(dict(vals, width='4', aggregation='count'), 'sale.order', False, False, 'date_order', "[]", aggregation='count')
                model = self._builder_find_model('sale.order')
                list_fields = [field(model, fname).id for fname in ['name', 'partner_id', 'date_order', 'state', 'amount_total'] if field(model, fname)]
                vals['list_field_ids'] = [(6, 0, list_fields)]
            elif key in ('pie', 'doughnut', 'polar_area', 'funnel'):
                vals = set_odoo(dict(vals, aggregation='count'), 'sale.order', False, 'state', 'date_order', "[]", aggregation='count')
            elif key in ('radial', 'bullet', 'tile'):
                vals = set_odoo(dict(vals, target_value=100000, width='1' if key == 'tile' else '2'), 'sale.order', 'amount_total', False, 'date_order', "[('state','in',['sale','done'])]", use_currency=True)
            else:
                vals = set_odoo(vals, 'sale.order', 'amount_total', 'date_order', 'date_order', "[('state','in',['sale','done'])]", use_currency=True)

        item = item_model.create(vals)
        return {'id': item.id, 'name': item.name}

    @api.model
    def reorder_items(self, dashboard_id, ordered_item_ids):
        dashboard = self.browse(int(dashboard_id))
        dashboard.ensure_one()
        if not dashboard._user_can_access():
            raise UserError(_('No tienes acceso a este dashboard.'))
        if not self.env.user.has_group('vlf_dashboard_pro_ferre.group_vlf_dashboard_manager'):
            raise UserError(_('Solo un usuario administrador del dashboard puede reordenar elementos.'))
        ordered_item_ids = [int(item_id) for item_id in (ordered_item_ids or [])]
        items = self.env['vlf.dashboard.item'].sudo().search([('dashboard_id', '=', dashboard.id), ('id', 'in', ordered_item_ids)])
        for index, item_id in enumerate(ordered_item_ids, start=1):
            item = items.filtered(lambda rec: rec.id == item_id)
            if item:
                item.sequence = index * 10
        return True

    def action_open_client(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'name': self.name,
            'tag': 'vlf_dashboard_pro_ferre.client_action',
            'params': {'dashboard_id': self.id},
        }

    @api.model
    def duplicate_dashboard(self, dashboard_id):
        dashboard = self.browse(int(dashboard_id))
        dashboard.ensure_one()
        new_dashboard = dashboard.copy({'name': _('%s (copia)') % dashboard.name, 'is_predefined': False})
        return {'id': new_dashboard.id, 'name': new_dashboard.name}

    @api.model
    def export_dashboard_json(self, dashboard_id):
        dashboard = self.browse(int(dashboard_id))
        dashboard.ensure_one()
        data = {
            'name': dashboard.name,
            'description': dashboard.description,
            'layout_mode': dashboard.layout_mode,
            'theme': dashboard.theme,
            'color_palette': dashboard.color_palette,
            'auto_refresh': dashboard.auto_refresh,
            'auto_refresh_seconds': dashboard.auto_refresh_seconds,
            'enable_realtime': dashboard.enable_realtime,
            'enable_advanced_filters': dashboard.enable_advanced_filters,
            'custom_filters': [],
            'items': [],
        }
        for cfilter in dashboard.filter_ids.sorted(lambda f: f.sequence):
            data['custom_filters'].append(cfilter.export_definition())
        for item in dashboard.item_ids.sorted(lambda i: i.sequence):
            data['items'].append(item.export_definition())
        return json.dumps(data, ensure_ascii=False, indent=2)

    @api.model
    def import_dashboard_json(self, json_payload):
        try:
            data = json.loads(json_payload or '{}')
        except Exception as exc:
            raise UserError(_('JSON inválido: %s') % exc)
        if not data.get('name'):
            raise UserError(_('El archivo JSON no contiene nombre de dashboard.'))
        dashboard = self.create({
            'name': data['name'],
            'description': data.get('description'),
            'layout_mode': data.get('layout_mode') or 'grid',
            'theme': data.get('theme') or 'light',
            'color_palette': data.get('color_palette') or 'business',
            'auto_refresh': bool(data.get('auto_refresh')),
            'auto_refresh_seconds': int(data.get('auto_refresh_seconds') or 60),
            'enable_realtime': bool(data.get('enable_realtime')),
            'enable_advanced_filters': bool(data.get('enable_advanced_filters', True)),
        })
        for definition in data.get('custom_filters', []):
            self.env['vlf.dashboard.filter'].create_from_definition(dashboard, definition)
        for definition in data.get('items', []):
            self.env['vlf.dashboard.item'].create_from_definition(dashboard, definition)
        return {'id': dashboard.id, 'name': dashboard.name}


class VlfDashboardFilter(models.Model):
    _name = 'vlf.dashboard.filter'
    _description = 'Tecnodyne Dashboard Filter'
    _order = 'dashboard_id, sequence, name'

    dashboard_id = fields.Many2one('vlf.dashboard', required=True, ondelete='cascade')
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    key = fields.Char(required=True, copy=False, help='Identificador técnico usado por el dashboard, por ejemplo: cliente, producto, vendedor.')
    field_name = fields.Char(required=True, help='Campo técnico principal a filtrar. Puede ser simple como partner_id o con relación como order_id.partner_id.')
    alternate_field_names = fields.Text(string='Campos alternos', help='Campos alternos para otros modelos del mismo dashboard. Escribe uno por línea, por ejemplo order_id.partner_id o move_id.partner_id.')
    value_type = fields.Selection([
        ('char', 'Texto'),
        ('number', 'Número'),
        ('many2one', 'Registro por ID'),
        ('date', 'Fecha'),
        ('boolean', 'Sí/No'),
        ('selection', 'Selección manual'),
    ], default='char', required=True)
    operator = fields.Selection([
        ('=', 'Igual a'),
        ('!=', 'Distinto de'),
        ('ilike', 'Contiene'),
        ('not ilike', 'No contiene'),
        ('>', 'Mayor que'),
        ('>=', 'Mayor o igual que'),
        ('<', 'Menor que'),
        ('<=', 'Menor o igual que'),
        ('in', 'Está en lista'),
        ('not in', 'No está en lista'),
    ], default='=', required=True)
    placeholder = fields.Char()
    default_value = fields.Char(help='Valor opcional que se aplica aunque el usuario no escriba nada.')
    option_values = fields.Text(help='Solo para selección manual. Usa una opción por línea: valor:Etiqueta. Ejemplo: sale:Venta confirmada')
    help_text = fields.Char()

    _sql_constraints = [
        ('dashboard_filter_key_unique', 'unique(dashboard_id, key)', 'La clave del filtro debe ser única por dashboard.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name') and not vals.get('key'):
                vals['key'] = self._slugify(vals['name'])
        return super().create(vals_list)

    def write(self, vals):
        # Keep an existing key stable because it may be used by saved dashboard filters.
        if vals.get('name') and 'key' not in vals:
            for record in self.filtered(lambda rec: not rec.key):
                record.key = self._slugify(vals['name'])
        return super().write(vals)

    @api.model
    def _slugify(self, value):
        value = (value or '').strip().lower()
        value = re.sub(r'[^a-z0-9_]+', '_', value)
        value = re.sub(r'_+', '_', value).strip('_')
        return value or 'filtro'

    def _get_options_payload(self):
        self.ensure_one()
        options = []
        for line in (self.option_values or '').splitlines():
            line = line.strip()
            if not line:
                continue
            if ':' in line:
                value, label = line.split(':', 1)
            else:
                value, label = line, line
            options.append({'value': value.strip(), 'label': label.strip()})
        return options

    def export_definition(self):
        self.ensure_one()
        return {
            'name': self.name,
            'active': self.active,
            'sequence': self.sequence,
            'key': self.key,
            'field_name': self.field_name,
            'alternate_field_names': self.alternate_field_names,
            'value_type': self.value_type,
            'operator': self.operator,
            'placeholder': self.placeholder,
            'default_value': self.default_value,
            'option_values': self.option_values,
            'help_text': self.help_text,
        }

    @api.model
    def create_from_definition(self, dashboard, definition):
        return self.create({
            'dashboard_id': dashboard.id,
            'name': definition.get('name') or _('Filtro importado'),
            'active': bool(definition.get('active', True)),
            'sequence': definition.get('sequence') or 10,
            'key': definition.get('key'),
            'field_name': definition.get('field_name') or 'name',
            'alternate_field_names': definition.get('alternate_field_names'),
            'value_type': definition.get('value_type') or 'char',
            'operator': definition.get('operator') or '=',
            'placeholder': definition.get('placeholder'),
            'default_value': definition.get('default_value'),
            'option_values': definition.get('option_values'),
            'help_text': definition.get('help_text'),
        })
