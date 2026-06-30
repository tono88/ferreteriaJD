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
        payload = super().get_dashboard_payload(dashboard_id=dashboard_id, filters=filters)
        if payload.get('dashboard'):
            payload['dashboard']['company_ids'] = [self.env.company.id]
        payload.setdefault('filters', {})['company_id'] = self.env.company.id
        return payload
