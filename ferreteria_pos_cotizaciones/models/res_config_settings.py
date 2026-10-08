from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_create_so = fields.Boolean(
        related="pos_config_id.create_so",
        readonly=False,
    )
