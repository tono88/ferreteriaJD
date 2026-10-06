# -*- coding: utf-8 -*-

from odoo import fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    thermal_receipt_commercial_name = fields.Char(
        string="Nombre comercial en ticket térmico",
        help="Nombre de la sucursal que aparecerá en el ticket térmico de 80 mm.",
    )
    thermal_receipt_address = fields.Text(
        string="Dirección en ticket térmico",
        help="Dirección de la sucursal que aparecerá en el ticket térmico de 80 mm.",
    )
    thermal_receipt_phone = fields.Char(
        string="Teléfono en ticket térmico",
        help="Teléfono de la sucursal. Déjelo vacío cuando no haya un dato confirmado.",
    )
