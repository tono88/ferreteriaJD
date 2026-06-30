# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

from .metric_service import VlfDashboardMetricService


class VlfDashboardItem(models.Model):
    _inherit = 'vlf.dashboard.item'

    metric_key = fields.Char(string='Métrica oficial', index=True, copy=False)
    managed_by_reports = fields.Boolean(string='Administrado por Dashboard Reports', default=False, copy=False)
    preset_version = fields.Integer(string='Versión del preset', default=0, copy=False)

    def _field_path_is_valid(self, model, field_path):
        """Validate every segment of a relational field path.

        The base dashboard only checks the first segment. For example,
        ``order_id.warehouse_id`` looks valid on ``pos.order.line`` because
        ``order_id`` exists, even though ``warehouse_id`` does not exist on
        ``pos.order``. This method prevents selecting such invalid paths.
        """
        current_model = model
        parts = [part for part in (field_path or '').split('.') if part]
        if not parts:
            return False
        for index, part in enumerate(parts):
            field = current_model._fields.get(part)
            if not field:
                return False
            if index < len(parts) - 1:
                comodel_name = getattr(field, 'comodel_name', False)
                if not comodel_name:
                    return False
                try:
                    current_model = self.env[comodel_name]
                except KeyError:
                    return False
        return True

    def _resolve_custom_filter_field(self, cfilter, model):
        """Return the first fully valid field path for the item model."""
        for field_name in self._custom_filter_field_candidates(cfilter):
            if self._field_path_is_valid(model, field_name):
                return field_name
        return False

    def _apply_dashboard_custom_filters(self, domain, filters=None):
        """Ignore empty ``False`` values for non-boolean custom filters.

        Selection widgets send ``False`` when the user leaves them on
        "Todos". The base engine treats that as a real domain value and can
        generate leaves such as ``('warehouse_id', '=', False)``.
        """
        clean_filters = dict(filters or {})
        custom_values = dict(clean_filters.get('custom') or {})
        for cfilter in self.dashboard_id.filter_ids.filtered('active'):
            if cfilter.value_type != 'boolean' and custom_values.get(cfilter.key) is False:
                custom_values.pop(cfilter.key, None)
        clean_filters['custom'] = custom_values
        return super()._apply_dashboard_custom_filters(domain, clean_filters)

    def _eval_domain(self, filters=None):
        self.ensure_one()
        filters = dict(filters or {})
        # La instalación usa una sola compañía. Nunca se confía en un company_id
        # recibido desde el navegador.
        filters['company_id'] = self.env.company.id
        domain = super()._eval_domain(filters=filters)

        if self.data_source == 'odoo' and self.model_id:
            model = self.env[self.model_id.model]
            if 'company_id' in model._fields:
                domain.append(('company_id', '=', self.env.company.id))
            if self.model_id.model == 'stock.quant':
                domain.append(('location_id.usage', '=', 'internal'))

        # Para campos Datetime, los límites se convierten desde la zona horaria
        # del usuario hacia UTC y la fecha final se trata como inclusiva.
        if self.data_source == 'odoo' and self.date_field_id and self.date_field_id.ttype == 'datetime':
            field_name = self.date_field_id.name
            date_from = filters.get('date_from')
            date_to = filters.get('date_to')
            if date_from or date_to:
                domain = [
                    leaf for leaf in domain
                    if not (
                        isinstance(leaf, (list, tuple)) and len(leaf) == 3
                        and leaf[0] == field_name
                        and leaf[1] in ('>=', '<=')
                        and str(leaf[2]) in (str(date_from), str(date_to))
                    )
                ]
                utc_from, utc_to = VlfDashboardMetricService(self.env)._date_bounds(filters)
                if utc_from:
                    domain.append((field_name, '>=', utc_from))
                if utc_to:
                    domain.append((field_name, '<', utc_to))
        return domain

    def _sort_pairs(self, pairs):
        self.ensure_one()
        # read_group ya devuelve los grupos temporales en orden cronológico.
        # No deben reordenarse por el importe.
        if self.groupby_field_id and self.groupby_field_id.ttype in ('date', 'datetime'):
            result = list(pairs)
            if self.limit and self.limit > 0:
                result = result[-self.limit:]
            return result
        return super()._sort_pairs(pairs)

    def _get_odoo_chart_data(self, filters=None):
        self.ensure_one()
        if not self.model_id:
            return {'labels': [], 'values': [], 'rows': [], 'total': 0}
        model = self.env[self.model_id.model].sudo(False)
        domain = self._eval_domain(filters)

        if self.item_type == 'list':
            fields_to_read = self.list_field_ids.mapped('name')[:10] or ['display_name']
            rows = model.search_read(domain, fields_to_read, limit=max(self.limit or 20, 1), order='id desc')
            clean_rows = [
                {key: self._format_label(value) for key, value in row.items() if key != 'id'}
                for row in rows
            ]
            return {'labels': [], 'values': [], 'rows': clean_rows, 'total': model.search_count(domain)}

        if self.item_type == 'map':
            return self._get_map_data(model, domain)

        if not self.groupby_field_id:
            if self.aggregation == 'count' or not self.measure_field_id:
                value = model.search_count(domain)
            else:
                field_name = self.measure_field_id.name
                groups = model.read_group(domain, [f'{field_name}:{self.aggregation}'], [])
                value = groups[0].get(field_name, 0.0) if groups else 0.0
            value = float(value or 0.0)
            return {'labels': [self.name], 'values': [value], 'rows': [], 'total': value}

        groupby_key = self._read_groupby_key()
        fields_list = []
        if self.aggregation != 'count' and self.measure_field_id:
            fields_list.append(f'{self.measure_field_id.name}:{self.aggregation}')
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
            raw_pairs.append((label, float(value or 0.0)))

        if self.aggregation == 'count' or not self.measure_field_id:
            global_total = float(model.search_count(domain))
        else:
            field_name = self.measure_field_id.name
            totals = model.read_group(domain, [f'{field_name}:{self.aggregation}'], [])
            global_total = float(totals[0].get(field_name, 0.0) or 0.0) if totals else 0.0

        pairs = self._sort_pairs(raw_pairs)
        labels = [pair[0] for pair in pairs]
        raw_values = [pair[1] for pair in pairs]
        values = self._apply_cumulative(raw_values)
        total = values[-1] if self.cumulative and values else global_total
        return {'labels': labels, 'values': values, 'rows': [], 'total': total}

    def _get_dataset_chart_data(self, filters=None):
        data = super()._get_dataset_chart_data(filters=filters)
        if self.cumulative and data.get('values'):
            data['total'] = data['values'][-1]
        return data

    def get_payload(self, filters=None):
        self.ensure_one()
        if not self.metric_key:
            return super().get_payload(filters=filters)

        metric_data = VlfDashboardMetricService(self.env).get_metric_payload(
            self.metric_key,
            filters=filters or {},
            limit=max(self.limit or 12, 1),
        )
        currency_symbol = self.currency_id.symbol if self.currency_id else self.env.company.currency_id.symbol
        return {
            'id': self.id,
            'name': self.name,
            'type': self.item_type,
            'sequence': self.sequence,
            'width': self.width,
            'height': self.height,
            'help_text': self.help_text or '',
            'icon': self.icon or '',
            'labels': metric_data.get('labels', []),
            'values': metric_data.get('values', []),
            'rows': metric_data.get('rows', []),
            'total': metric_data.get('total', 0),
            'target_value': self.target_value,
            'target_label': self.target_label or _('Meta'),
            'show_target': self.show_target,
            'show_values': self.show_values,
            'show_legend': self.show_legend,
            'show_total': self.show_total,
            'list_style': self.list_style,
            'unit_prefix': self.unit_prefix or (currency_symbol if metric_data.get('currency', False) else ''),
            'unit_suffix': self.unit_suffix or '',
            'number_system': self.number_system,
            'precision_digits': self.precision_digits,
            'color_palette': self.color_palette if self.color_palette != 'inherit' else self.dashboard_id.color_palette,
            'custom_color': self.custom_color or '',
            'background_color': self.background_color or '',
            'allow_drill_down': bool(self.allow_drill_down and metric_data.get('drill_model')),
            'model': metric_data.get('drill_model', ''),
        }

    @api.model
    def get_item_action(self, item_id, filters=None):
        item = self.browse(int(item_id))
        item.ensure_one()
        if not item.metric_key:
            return super().get_item_action(item_id=item_id, filters=filters)
        return VlfDashboardMetricService(self.env).get_metric_action(
            item.metric_key,
            filters=filters or {},
            item_name=item.name,
        )
