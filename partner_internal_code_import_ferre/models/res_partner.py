# -*- coding: utf-8 -*-

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    # El módulo original define internal_code como readonly=True.
    # Este parche cambia únicamente esa propiedad ORM para que el campo
    # sea compatible con el importador estándar de Odoo.
    internal_code = fields.Char(readonly=False)
