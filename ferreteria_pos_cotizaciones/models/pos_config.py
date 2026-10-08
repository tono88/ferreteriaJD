from odoo import fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    create_so = fields.Boolean(
        string="Permitir crear cotizaciones desde el POS",
        default=True,
    )
