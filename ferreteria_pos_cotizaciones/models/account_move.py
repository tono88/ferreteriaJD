# Copyright 2026 Ferretería JD. LGPL-3.
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    ferreteria_pos_sale_order_id = fields.Many2one(
        "sale.order",
        string="Pedido de venta origen del POS",
        readonly=True,
        copy=False,
        index=True,
        help="Vínculo informativo con la cotización. La factura se genera "
             "una sola vez en POS; no se duplican líneas de facturación de Ventas.",
    )
