# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    internal_correlative = fields.Char(
        string="Correlativo interno POS",
        index=True,
        copy=False,
    )
