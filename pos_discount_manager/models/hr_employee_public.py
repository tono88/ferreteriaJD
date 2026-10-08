# Copyright 2025 Cybrosys Technologies Pvt. Ltd.
# Adaptación Ferretería JD 2026. AGPL-3.
from odoo import api, fields, models


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    limited_discount = fields.Integer(
        string="Límite de descuento (%)",
        related="employee_id.limited_discount",
        readonly=True,
    )

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields_to_load = super()._load_pos_data_fields(config_id)
        if "limited_discount" not in fields_to_load:
            fields_to_load.append("limited_discount")
        return fields_to_load
