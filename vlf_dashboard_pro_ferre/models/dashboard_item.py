# -*- coding: utf-8 -*-
import json
import math
from datetime import date, datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval


NUMERIC_TYPES = ('integer', 'float', 'monetary')
DATE_TYPES = ('date', 'datetime')


class VlfDashboardItem(models.Model):
    _name = 'vlf.dashboard.item'
    _description = 'Tecnodyne Dashboard Item'
    _order = 'dashboard_id, sequence, name'

    dashboard_id = fields.Many2one('vlf.dashboard', required=True, ondelete='cascade')
    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    help_text = fields.Char()
    icon = fields.Char(default='fa-bar-chart')

    item_type = fields.Selection([
        ('tile', 'Tile / KPI'),
        ('line', 'Line Chart'),
        ('list', 'List View'),
        ('bar', 'Bar Chart'),
        ('horizontal_bar', 'Horizontal Bar Chart'),
        ('todo', 'To-do Item'),
        ('polar_area', 'Polar Area Chart'),
        ('pie', 'Pie Chart'),
        ('doughnut', 'Doughnut Chart'),
        ('flower', 'Flower Chart'),
        ('funnel', 'Funnel Chart'),
        ('radial', 'Radial Chart'),
        ('bullet', 'Bullet Chart'),
        ('scatter', 'Scatter Chart'),
        ('radar', 'Radar Chart'),
        ('map', 'Map View'),
        ('area', 'Area Chart'),
    ], required=True, default='tile')

    width = fields.Selection([
        ('1', '1 columna'),
        ('2', '2 columnas'),
        ('3', '3 columnas'),
        ('4', '4 columnas'),
    ], default='1')
    height = fields.Selection([
        ('small', 'Pequeño'),
        ('medium', 'Mediano'),
        ('large', 'Grande'),
    ], default='medium')

    data_source = fields.Selection([
        ('odoo', 'Odoo'),
        ('dataset', 'Dataset Excel/CSV'),
    ], default='odoo', required=True)
    model_id = fields.Many2one('ir.model', string='Modelo Odoo', ondelete='cascade')
    model_name = fields.Char(related='model_id.model', store=True)
    dataset_id = fields.Many2one('vlf.dashboard.dataset')
    dataset_group_key = fields.Char(string='Columna de agrupación')
    dataset_measure_key = fields.Char(string='Columna de medida')

    domain = fields.Text(default='[]', help='Dominio Odoo en formato Python. Variables disponibles: UID, MY_COMPANY, COMPANY_IDS, TODAY, DATE_FROM, DATE_TO.')
    measure_field_id = fields.Many2one('ir.model.fields', string='Medida', domain="[('model_id', '=', model_id)]")
    groupby_field_id = fields.Many2one('ir.model.fields', string='Agrupar por', domain="[('model_id', '=', model_id)]")
    subgroup_field_id = fields.Many2one('ir.model.fields', string='Subagrupar por', domain="[('model_id', '=', model_id)]")
    date_field_id = fields.Many2one('ir.model.fields', string='Campo fecha', domain="[('model_id', '=', model_id), ('ttype', 'in', ['date', 'datetime'])]")
    groupby_interval = fields.Selection([
        ('day', 'Día'),
        ('week', 'Semana'),
        ('month', 'Mes'),
        ('quarter', 'Trimestre'),
        ('year', 'Año'),
    ], default='month')
    aggregation = fields.Selection([
        ('count', 'Conteo'),
        ('sum', 'Suma'),
        ('avg', 'Promedio'),
        ('min', 'Mínimo'),
        ('max', 'Máximo'),
    ], default='sum')
    limit = fields.Integer(default=12)
    sort_by = fields.Selection([
        ('label', 'Etiqueta'),
        ('value', 'Valor'),
    ], default='value')
    sort_direction = fields.Selection([
        ('asc', 'Ascendente'),
        ('desc', 'Descendente'),
    ], default='desc')
    cumulative = fields.Boolean(string='Acumulado')

    target_value = fields.Float(string='Meta')
    target_label = fields.Char(default='Meta')
    show_target = fields.Boolean(default=True)
    show_values = fields.Boolean(default=True)
    show_legend = fields.Boolean(default=True)
    show_total = fields.Boolean(default=True)
    list_style = fields.Selection([
        ('table', 'Tabla'),
        ('cards', 'Tarjetas'),
    ], default='table')

    unit_prefix = fields.Char(string='Prefijo unidad')
    unit_suffix = fields.Char(string='Sufijo unidad')
    currency_id = fields.Many2one('res.currency')
    number_system = fields.Selection([
        ('default', 'Normal'),
        ('compact', 'Compacto 1.2K / 3.4M'),
        ('indian', 'Indian Lakh/Crore'),
    ], default='default')
    precision_digits = fields.Integer(default=2)

    color_palette = fields.Selection([
        ('inherit', 'Heredar del dashboard'),
        ('classic', 'Clásica'),
        ('business', 'Empresarial'),
        ('pastel', 'Pastel'),
        ('contrast', 'Contraste'),
        ('mono', 'Monocromática'),
    ], default='inherit')
    custom_color = fields.Char()
    background_color = fields.Char()

    allow_drill_down = fields.Boolean(default=True)
    open_view_mode = fields.Char(default='list,form,pivot,graph')

    list_field_ids = fields.Many2many('ir.model.fields', 'vlf_dashboard_item_list_field_rel', 'item_id', 'field_id', string='Campos de lista')


    def _coerce_custom_filter_value(self, cfilter, value):
        operator = cfilter.operator
        if operator in ('in', 'not in'):
            values = value if isinstance(value, list) else [v.strip() for v in str(value).split(',') if v.strip()]
            if cfilter.value_type in ('number', 'many2one'):
                parsed = []
                for item in values:
                    try:
                        parsed.append(int(float(item)) if cfilter.value_type == 'many2one' else float(item))
                    except Exception:
                        continue
                return parsed
            if cfilter.value_type == 'boolean':
                return [v in (True, '1', 'true', 'True', 'yes', 'on', 1) for v in values]
            return values
        if cfilter.value_type in ('number', 'many2one'):
            try:
                return int(float(value)) if cfilter.value_type == 'many2one' else float(value)
            except Exception:
                raise UserError(_('El filtro %s debe ser numérico o un ID válido.') % cfilter.name)
        if cfilter.value_type == 'boolean':
            return value in (True, '1', 'true', 'True', 'yes', 'on', 1)
        return value

    def _custom_filter_field_candidates(self, cfilter):
        values = []
        if cfilter.field_name:
            values.append(cfilter.field_name.strip())
        raw = (cfilter.alternate_field_names or '').replace(',', '\n').replace(';', '\n')
        for line in raw.splitlines():
            line = line.strip()
            if line and line not in values:
                values.append(line)
        return values

    def _resolve_custom_filter_field(self, cfilter, model):
        for field_name in self._custom_filter_field_candidates(cfilter):
            first_field = field_name.split('.')[0]
            if first_field in model._fields:
                return field_name
        return False

    def _apply_dashboard_custom_filters(self, domain, filters=None):
        self.ensure_one()
        if not self.model_id:
            return domain
        model = self.env[self.model_id.model]
        custom_values = (filters or {}).get('custom') or {}
        for cfilter in self.dashboard_id.filter_ids.filtered('active').sorted(lambda f: f.sequence):
            field_name = self._resolve_custom_filter_field(cfilter, model)
            if not field_name:
                # The same dashboard can contain different models. A custom filter only affects items where a compatible field exists.
                continue
            value = custom_values.get(cfilter.key)
            if (value is None or value == '') and cfilter.default_value not in (None, ''):
                value = cfilter.default_value
            if value is None or value == '':
                continue
            value = self._coerce_custom_filter_value(cfilter, value)
            if cfilter.operator in ('in', 'not in') and not value:
                continue
            domain.append((field_name, cfilter.operator, value))
        return domain

    def _eval_domain(self, filters=None):
        self.ensure_one()
        filters = filters or {}
        today = date.today()
        date_from = filters.get('date_from') or None
        date_to = filters.get('date_to') or None
        names = {
            'UID': self.env.uid,
            'MY_COMPANY': self.env.company.id,
            'COMPANY_IDS': self.env.companies.ids,
            'TODAY': today.isoformat(),
            'DATE_FROM': date_from,
            'DATE_TO': date_to,
        }
        try:
            domain = safe_eval(self.domain or '[]', names)
        except Exception as exc:
            raise UserError(_('Dominio inválido en %s: %s') % (self.name, exc))
        if not isinstance(domain, list):
            raise UserError(_('El dominio del item %s debe ser una lista.') % self.name)
        if self.data_source == 'odoo' and self.date_field_id:
            field_name = self.date_field_id.name
            if date_from:
                domain.append((field_name, '>=', date_from))
            if date_to:
                domain.append((field_name, '<=', date_to))
        if self.data_source == 'odoo' and self.model_id:
            model = self.env[self.model_id.model]
            if 'company_id' in model._fields:
                company_id = filters.get('company_id') or self.env.company.id
                domain.append(('company_id', 'in', [int(company_id)] if company_id else self.env.companies.ids))
            domain = self._apply_dashboard_custom_filters(domain, filters)
        return domain

    def _format_label(self, raw_value):
        if isinstance(raw_value, (list, tuple)) and len(raw_value) >= 2:
            return raw_value[1] or _('Sin valor')
        if isinstance(raw_value, bool):
            return _('Sí') if raw_value else _('No')
        return str(raw_value or _('Sin valor'))

    def _read_groupby_key(self):
        self.ensure_one()
        if not self.groupby_field_id:
            return False
        key = self.groupby_field_id.name
        if self.groupby_field_id.ttype in DATE_TYPES and self.groupby_interval:
            key = '%s:%s' % (key, self.groupby_interval)
        return key

    def _read_measure(self):
        self.ensure_one()
        if self.aggregation == 'count' or not self.measure_field_id:
            return '__count'
        return self.measure_field_id.name

    def _extract_group_value(self, group, measure_name):
        self.ensure_one()
        if self.aggregation == 'count' or measure_name == '__count':
            return group.get('__count', 0)
        value = group.get(measure_name, 0.0) or 0.0
        return float(value)

    def _sort_pairs(self, pairs):
        reverse = self.sort_direction == 'desc'
        if self.sort_by == 'label':
            pairs = sorted(pairs, key=lambda p: str(p[0]).lower(), reverse=reverse)
        else:
            pairs = sorted(pairs, key=lambda p: float(p[1] or 0), reverse=reverse)
        if self.limit and self.limit > 0:
            pairs = pairs[:self.limit]
        return pairs

    def _apply_cumulative(self, values):
        if not self.cumulative:
            return values
        total = 0
        result = []
        for value in values:
            total += value or 0
            result.append(total)
        return result

    def _get_odoo_chart_data(self, filters=None):
        self.ensure_one()
        if not self.model_id:
            return {'labels': [], 'values': [], 'rows': [], 'total': 0}
        model = self.env[self.model_id.model].sudo(False)
        domain = self._eval_domain(filters)
        measure = self._read_measure()

        if self.item_type == 'list':
            fields_to_read = self.list_field_ids.mapped('name')[:10]
            if not fields_to_read:
                fields_to_read = ['display_name']
            rows = model.search_read(domain, fields_to_read, limit=max(self.limit or 20, 1), order='id desc')
            clean_rows = []
            for row in rows:
                clean_rows.append({k: self._format_label(v) for k, v in row.items() if k != 'id'})
            return {'labels': [], 'values': [], 'rows': clean_rows, 'total': len(clean_rows)}

        if self.item_type == 'map':
            return self._get_map_data(model, domain)

        if not self.groupby_field_id:
            if self.aggregation == 'count' or not self.measure_field_id:
                value = model.search_count(domain)
            else:
                groups = model.read_group(domain, [self.measure_field_id.name], [])
                value = groups[0].get(self.measure_field_id.name, 0.0) if groups else 0.0
            return {'labels': [self.name], 'values': [float(value or 0)], 'rows': [], 'total': float(value or 0)}

        groupby_key = self._read_groupby_key()
        fields_list = []
        if self.aggregation != 'count' and self.measure_field_id:
            fields_list.append('%s:%s' % (self.measure_field_id.name, self.aggregation))
        groups = model.read_group(domain, fields_list, [groupby_key], lazy=False)
        raw_pairs = []
        group_field_name = self.groupby_field_id.name
        for group in groups:
            raw = group.get(group_field_name) or group.get(groupby_key)
            label = self._format_label(raw)
            if self.aggregation == 'count' or not self.measure_field_id:
                value = group.get('__count', 0)
            else:
                value = group.get(self.measure_field_id.name, 0.0) or 0.0
            raw_pairs.append((label, float(value or 0)))
        pairs = self._sort_pairs(raw_pairs)
        labels = [p[0] for p in pairs]
        values = self._apply_cumulative([p[1] for p in pairs])
        return {'labels': labels, 'values': values, 'rows': [], 'total': sum(values or [])}

    def _get_dataset_chart_data(self, filters=None):
        self.ensure_one()
        if not self.dataset_id:
            return {'labels': [], 'values': [], 'rows': [], 'total': 0}
        rows = self.dataset_id.get_rows_as_dicts()
        group_key = self.dataset_group_key
        measure_key = self.dataset_measure_key
        if self.item_type == 'list':
            return {'labels': [], 'values': [], 'rows': rows[:max(self.limit or 20, 1)], 'total': len(rows)}
        grouped = {}
        for row in rows:
            label = str(row.get(group_key) or _('Sin valor')) if group_key else self.name
            if self.aggregation == 'count' or not measure_key:
                value = 1.0
            else:
                raw = str(row.get(measure_key) or '0').replace(',', '')
                try:
                    value = float(raw)
                except Exception:
                    value = 0.0
            if self.aggregation in ('count', 'sum', 'avg'):
                grouped.setdefault(label, []).append(value)
            elif self.aggregation == 'min':
                grouped[label] = [min(grouped.get(label, [value])[0], value)]
            elif self.aggregation == 'max':
                grouped[label] = [max(grouped.get(label, [value])[0], value)]
        pairs = []
        for label, vals in grouped.items():
            value = sum(vals) / len(vals) if self.aggregation == 'avg' and vals else sum(vals)
            pairs.append((label, float(value or 0)))
        pairs = self._sort_pairs(pairs)
        labels = [p[0] for p in pairs]
        values = self._apply_cumulative([p[1] for p in pairs])
        return {'labels': labels, 'values': values, 'rows': [], 'total': sum(values or [])}

    def _get_map_data(self, model, domain):
        self.ensure_one()
        points = []
        limit = max(self.limit or 30, 1)
        if model._name == 'res.partner' and 'partner_latitude' in model._fields and 'partner_longitude' in model._fields:
            partners = model.search(domain + [('partner_latitude', '!=', False), ('partner_longitude', '!=', False)], limit=limit)
            for partner in partners:
                points.append({
                    'label': partner.display_name,
                    'lat': partner.partner_latitude,
                    'lng': partner.partner_longitude,
                    'value': 1,
                })
        elif 'partner_id' in model._fields:
            records = model.search(domain, limit=limit)
            for rec in records:
                partner = rec.partner_id
                if partner and getattr(partner, 'partner_latitude', False) and getattr(partner, 'partner_longitude', False):
                    points.append({
                        'label': partner.display_name,
                        'lat': partner.partner_latitude,
                        'lng': partner.partner_longitude,
                        'value': 1,
                    })
        return {'labels': [p['label'] for p in points], 'values': [p['value'] for p in points], 'rows': points, 'total': len(points)}

    def _get_todo_data(self, filters=None):
        self.ensure_one()
        domain = [('dashboard_id', '=', self.dashboard_id.id)]
        todos = self.env['vlf.dashboard.todo'].search(domain, limit=max(self.limit or 20, 1), order='state, priority desc, deadline asc')
        rows = []
        for todo in todos:
            rows.append({
                'id': todo.id,
                'name': todo.name,
                'state': todo.state,
                'priority': todo.priority,
                'deadline': fields.Date.to_string(todo.deadline) if todo.deadline else '',
                'user': todo.user_id.name or '',
            })
        return {'labels': ['Abiertas', 'Hechas'], 'values': [len(todos.filtered(lambda t: t.state != 'done')), len(todos.filtered(lambda t: t.state == 'done'))], 'rows': rows, 'total': len(rows)}

    def get_payload(self, filters=None):
        self.ensure_one()
        if self.item_type == 'todo':
            data = self._get_todo_data(filters)
        elif self.data_source == 'dataset':
            data = self._get_dataset_chart_data(filters)
        else:
            data = self._get_odoo_chart_data(filters)
        currency_symbol = self.currency_id.symbol if self.currency_id else ''
        return {
            'id': self.id,
            'name': self.name,
            'type': self.item_type,
            'sequence': self.sequence,
            'width': self.width,
            'height': self.height,
            'help_text': self.help_text or '',
            'icon': self.icon or '',
            'labels': data.get('labels', []),
            'values': data.get('values', []),
            'rows': data.get('rows', []),
            'total': data.get('total', 0),
            'target_value': self.target_value,
            'target_label': self.target_label or _('Meta'),
            'show_target': self.show_target,
            'show_values': self.show_values,
            'show_legend': self.show_legend,
            'show_total': self.show_total,
            'list_style': self.list_style,
            'unit_prefix': self.unit_prefix or currency_symbol or '',
            'unit_suffix': self.unit_suffix or '',
            'number_system': self.number_system,
            'precision_digits': self.precision_digits,
            'color_palette': self.color_palette if self.color_palette != 'inherit' else self.dashboard_id.color_palette,
            'custom_color': self.custom_color or '',
            'background_color': self.background_color or '',
            'allow_drill_down': self.allow_drill_down and self.data_source == 'odoo' and bool(self.model_id),
            'model': self.model_id.model if self.model_id else '',
        }

    def get_error_payload(self, message):
        self.ensure_one()
        return {
            'id': self.id,
            'name': self.name,
            'type': 'error',
            'sequence': self.sequence,
            'width': self.width,
            'height': self.height,
            'labels': [],
            'values': [],
            'rows': [],
            'total': 0,
            'message': message,
            'show_values': True,
            'show_legend': False,
            'allow_drill_down': False,
        }

    @api.model
    def get_item_action(self, item_id, filters=None):
        item = self.browse(int(item_id))
        item.ensure_one()
        if item.data_source != 'odoo' or not item.model_id:
            return False
        # In Odoo 18, client-side doAction expects the explicit 'views' array.
        # Returning only view_mode can trigger: action.views is undefined.
        raw_modes = (item.open_view_mode or 'list,form').replace('tree', 'list')
        allowed_modes = {'list', 'form', 'pivot', 'graph', 'kanban', 'calendar'}
        views = []
        for mode in [part.strip() for part in raw_modes.split(',') if part.strip()]:
            if mode in allowed_modes and [False, mode] not in views:
                views.append([False, mode])
        if not views:
            views = [[False, 'list'], [False, 'form']]
        view_mode = ','.join([view[1] for view in views])
        return {
            'type': 'ir.actions.act_window',
            'name': item.name,
            'res_model': item.model_id.model,
            'views': views,
            'view_mode': view_mode,
            'domain': item._eval_domain(filters),
            'target': 'current',
            'context': dict(self.env.context or {}),
        }

    def export_definition(self):
        self.ensure_one()
        return {
            'name': self.name,
            'active': self.active,
            'sequence': self.sequence,
            'help_text': self.help_text,
            'icon': self.icon,
            'item_type': self.item_type,
            'width': self.width,
            'height': self.height,
            'data_source': self.data_source,
            'model': self.model_id.model if self.model_id else False,
            'dataset': self.dataset_id.name if self.dataset_id else False,
            'dataset_group_key': self.dataset_group_key,
            'dataset_measure_key': self.dataset_measure_key,
            'domain': self.domain,
            'measure_field': self.measure_field_id.name if self.measure_field_id else False,
            'groupby_field': self.groupby_field_id.name if self.groupby_field_id else False,
            'date_field': self.date_field_id.name if self.date_field_id else False,
            'groupby_interval': self.groupby_interval,
            'aggregation': self.aggregation,
            'limit': self.limit,
            'sort_by': self.sort_by,
            'sort_direction': self.sort_direction,
            'cumulative': self.cumulative,
            'target_value': self.target_value,
            'target_label': self.target_label,
            'show_target': self.show_target,
            'show_values': self.show_values,
            'show_legend': self.show_legend,
            'unit_prefix': self.unit_prefix,
            'unit_suffix': self.unit_suffix,
            'number_system': self.number_system,
            'precision_digits': self.precision_digits,
            'color_palette': self.color_palette,
            'allow_drill_down': self.allow_drill_down,
            'open_view_mode': self.open_view_mode,
        }

    @api.model
    def create_from_definition(self, dashboard, definition):
        model = self.env['ir.model'].search([('model', '=', definition.get('model'))], limit=1) if definition.get('model') else False
        def field_by_name(field_name):
            if not model or not field_name:
                return False
            return self.env['ir.model.fields'].search([('model_id', '=', model.id), ('name', '=', field_name)], limit=1)
        dataset = self.env['vlf.dashboard.dataset'].search([('name', '=', definition.get('dataset'))], limit=1) if definition.get('dataset') else False
        vals = {
            'dashboard_id': dashboard.id,
            'name': definition.get('name') or _('Item importado'),
            'active': bool(definition.get('active', True)),
            'sequence': definition.get('sequence') or 10,
            'help_text': definition.get('help_text'),
            'icon': definition.get('icon'),
            'item_type': definition.get('item_type') or 'tile',
            'width': str(definition.get('width') or '1'),
            'height': definition.get('height') or 'medium',
            'data_source': definition.get('data_source') or 'odoo',
            'model_id': model.id if model else False,
            'dataset_id': dataset.id if dataset else False,
            'dataset_group_key': definition.get('dataset_group_key'),
            'dataset_measure_key': definition.get('dataset_measure_key'),
            'domain': definition.get('domain') or '[]',
            'measure_field_id': field_by_name(definition.get('measure_field')).id if field_by_name(definition.get('measure_field')) else False,
            'groupby_field_id': field_by_name(definition.get('groupby_field')).id if field_by_name(definition.get('groupby_field')) else False,
            'date_field_id': field_by_name(definition.get('date_field')).id if field_by_name(definition.get('date_field')) else False,
            'groupby_interval': definition.get('groupby_interval') or 'month',
            'aggregation': definition.get('aggregation') or 'sum',
            'limit': definition.get('limit') or 12,
            'sort_by': definition.get('sort_by') or 'value',
            'sort_direction': definition.get('sort_direction') or 'desc',
            'cumulative': bool(definition.get('cumulative')),
            'target_value': definition.get('target_value') or 0.0,
            'target_label': definition.get('target_label') or 'Meta',
            'show_target': bool(definition.get('show_target', True)),
            'show_values': bool(definition.get('show_values', True)),
            'show_legend': bool(definition.get('show_legend', True)),
            'unit_prefix': definition.get('unit_prefix'),
            'unit_suffix': definition.get('unit_suffix'),
            'number_system': definition.get('number_system') or 'default',
            'precision_digits': definition.get('precision_digits') or 2,
            'color_palette': definition.get('color_palette') or 'inherit',
            'allow_drill_down': bool(definition.get('allow_drill_down', True)),
            'open_view_mode': definition.get('open_view_mode') or 'list,form,pivot,graph',
        }
        return self.create(vals)
