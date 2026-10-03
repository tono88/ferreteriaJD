# -*- coding: utf-8 -*-
from odoo import api, fields, models


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
        return payload
