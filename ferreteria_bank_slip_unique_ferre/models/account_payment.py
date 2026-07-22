# -*- coding: utf-8 -*-
from odoo import api, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.model_create_multi
    def create(self, vals_list):
        registry = self.env["ferreteria.bank.slip.registry"]
        for vals in vals_list:
            if "bank_reference" in vals:
                vals["bank_reference"] = registry.clean_number(vals.get("bank_reference"))
        payments = super().create(vals_list)
        for payment in payments:
            registry.claim(payment, payment.bank_reference)
        return payments

    def write(self, vals):
        registry = self.env["ferreteria.bank.slip.registry"]
        if "bank_reference" in vals:
            vals["bank_reference"] = registry.clean_number(vals.get("bank_reference"))
        result = super().write(vals)
        if "bank_reference" in vals:
            for payment in self:
                registry.claim(payment, payment.bank_reference)
        return result
