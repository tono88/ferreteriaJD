# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PosOrderPayment(models.Model):
    _inherit = "pos.order.payment"

    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        related="pos_order_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    bank_slip_number = fields.Char(
        string="No. boleta bancaria",
        copy=False,
        index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        registry = self.env["ferreteria.bank.slip.registry"]
        for vals in vals_list:
            if "bank_slip_number" in vals:
                vals["bank_slip_number"] = registry.clean_number(vals.get("bank_slip_number"))
        payments = super().create(vals_list)
        for payment in payments:
            registry.claim(payment, payment.bank_slip_number)
        return payments

    def write(self, vals):
        registry = self.env["ferreteria.bank.slip.registry"]
        if "bank_slip_number" in vals:
            vals["bank_slip_number"] = registry.clean_number(vals.get("bank_slip_number"))
        result = super().write(vals)
        if "bank_slip_number" in vals:
            for payment in self:
                registry.claim(payment, payment.bank_slip_number)
        return result
