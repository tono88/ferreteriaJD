# Copyright 2025 Cybrosys Technologies Pvt. Ltd.
# Adaptación Ferretería JD 2026. AGPL-3.
from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    limited_discount = fields.Integer(
        string="Límite de descuento (%)",
        help="Porcentaje de descuento máximo sin autorización. Un valor de 0 mantiene el comportamiento original: sin límite.",
    )

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields_to_load = super()._load_pos_data_fields(config_id)
        for field_name in ("limited_discount", "parent_id"):
            if field_name not in fields_to_load:
                fields_to_load.append(field_name)
        # No cargar el PIN del supervisor: se sustituye por OTP verificado en servidor.
        return fields_to_load
