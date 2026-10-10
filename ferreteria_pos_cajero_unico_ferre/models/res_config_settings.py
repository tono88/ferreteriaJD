from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_ferreteria_cajero_unico = fields.Boolean(
        related="pos_config_id.ferreteria_cajero_unico",
        readonly=False,
    )
