# -*- coding: utf-8 -*-

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    ferreteria_receive_stock_min_alerts = fields.Boolean(
        string="Recibir alertas de reabastecimiento",
        default=False,
        help=(
            "Si está marcado, el usuario recibirá por correo las alertas de productos "
            "cuyo inventario pronosticado quede por debajo del mínimo configurado en "
            "una regla de reabastecimiento."
        ),
    )
