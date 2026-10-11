# -*- coding: utf-8 -*-
from odoo import api, fields, models

from .inventory_history import InventoryHistoryService


class VlfDashboard(models.Model):
    _inherit = 'vlf.dashboard'

    technical_key = fields.Char(string='Clave técnica', index=True, copy=False)
    preset_version = fields.Integer(string='Versión del preset', default=0, copy=False)
    managed_by_reports = fields.Boolean(string='Administrado por Dashboard Reports', default=False, copy=False)

    _sql_constraints = [
        ('vlf_dashboard_technical_key_unique', 'unique(technical_key)', 'La clave técnica del dashboard debe ser única.'),
    ]

    @api.model
    def get_dashboard_payload(self, dashboard_id=False, filters=None):
        filters = dict(filters or {})
        filters['custom'] = dict(filters.get('custom') or {})
        dashboard = self.browse(int(dashboard_id)) if dashboard_id else self.search([('active', '=', True)], limit=1)
        years = sorted({record.date.year for record in self.env['vlf.sales.order.fact'].sudo().search([('date', '!=', False)])}, reverse=True)
        if not years:
            years = [fields.Date.context_today(self).year]
        if dashboard and dashboard.managed_by_reports and not filters['custom'].get('year'):
            filters['custom']['year'] = str(years[0])
        payload = super().get_dashboard_payload(dashboard_id=dashboard_id, filters=filters)
        if payload.get('dashboard'):
            payload['dashboard']['company_ids'] = [self.env.company.id]
            for custom_filter in payload['dashboard'].get('custom_filters', []):
                if custom_filter.get('key') == 'year':
                    custom_filter['options'] = [
                        {'value': str(year), 'label': str(year)} for year in years
                    ]
        payload.setdefault('filters', {})['company_id'] = self.env.company.id

        # Inventario is the preconfigured operational stock dashboard. The
        # historical mode is purely a read-only alternate rendering; no
        # chart/domain definition is changed in the database.
        is_inventory = bool(
            dashboard and dashboard.name == 'Inventario'
            and dashboard.item_ids.filtered(
                lambda item: item.active and item.model_id.model == 'stock.quant'
            )
        )
        if payload.get('dashboard') and is_inventory:
            history = InventoryHistoryService(self.env)
            payload['dashboard']['inventory_history_enabled'] = True
            payload['dashboard']['inventory_warehouses'] = history.warehouse_options()
            if filters.get('inventory_mode') == 'history':
                snapshot = history.snapshot(
                    filters.get('inventory_date'),
                    filters.get('inventory_warehouse_id'),
                )
                originals = {data['id']: data for data in payload.get('items', [])}
                historical_items = []
                for item in dashboard.item_ids.filtered('active').sorted(lambda i: i.sequence):
                    if not item.model_id or item.model_id.model != 'stock.quant':
                        continue
                    data = history.item_data(item, snapshot)
                    if data is None:
                        continue  # no false "historical reserved" or unrelated cards
                    updated = dict(originals.get(item.id) or item.get_error_payload(''))
                    updated.update({
                        'type': item.item_type,
                        'name': item.name,
                        'labels': data['labels'],
                        'values': data['values'],
                        'rows': data['rows'],
                        'total': data['total'],
                        'allow_drill_down': False,  # current quants != historical detail
                    })
                    historical_items.append(updated)
                payload['items'] = historical_items
                payload['dashboard']['inventory_history_info'] = {
                    'date': filters.get('inventory_date'),
                    'provisional': snapshot['provisional'],
                    'warehouses': history.warehouse_summary(snapshot),
                }
        return payload
