from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PosConfig(models.Model):
    _inherit = "pos.config"

    ferreteria_cajero_unico = fields.Boolean(
        string="Cajero único según usuario de Odoo",
        help="Usar la cuenta de Odoo como cajero, sin pedir otro PIN ni permitir "
             "cambio de cajero. Requiere desactivar Iniciar sesión como empleado.",
    )

    @api.constrains("ferreteria_cajero_unico", "module_pos_hr")
    def _check_single_cashier_mode(self):
        for config in self:
            if config.ferreteria_cajero_unico and config.module_pos_hr:
                raise ValidationError(_(
                    "Para activar Cajero único, desactive primero "
                    "'Iniciar sesión como empleado' en este punto de venta."
                ))

    @api.model
    def _load_pos_data_fields(self, config_id):
        values = super()._load_pos_data_fields(config_id)
        if "ferreteria_cajero_unico" not in values:
            values.append("ferreteria_cajero_unico")
        return values
