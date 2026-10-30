# -*- coding: utf-8 -*-
from odoo import api, models

# An identity-only marker cannot be supplied through a JSON/RPC context.
# Only the register wizard may defer claims until all its payments exist.
_REGISTER_BATCH = object()


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def action_post(self):
        if self.env.context.get("_bank_slip_register_batch") is not _REGISTER_BATCH:
            registry = self.env["ferreteria.bank.slip.registry"]
            for payment in self:
                registry.claim(payment, payment.bank_reference)
        # The legacy payment_bank_reference_dup_check returns a popup instead
        # of posting legitimate siblings. The register wizard ignores that
        # return value, leaving draft journal entries and unpaid invoices.
        # Our historical registry already enforces stronger uniqueness, including
        # the trusted register batch (claimed atomically before it returns).
        payment = self.with_context(skip_bank_reference_dup_check=True)
        return super(AccountPayment, payment).action_post()

    @api.model_create_multi
    def create(self, vals_list):
        registry = self.env["ferreteria.bank.slip.registry"]
        for vals in vals_list:
            if "bank_reference" in vals:
                vals["bank_reference"] = registry.clean_number(vals.get("bank_reference"))
        payments = super().create(vals_list)
        if self.env.context.get("_bank_slip_register_batch") is not _REGISTER_BATCH:
            for payment in payments:
                registry.claim(payment, payment.bank_reference)
        return payments

    def write(self, vals):
        registry = self.env["ferreteria.bank.slip.registry"]
        if "bank_reference" in vals:
            vals["bank_reference"] = registry.clean_number(vals.get("bank_reference"))
        result = super().write(vals)
        if (("bank_reference" in vals or vals.get("state") in ("in_process", "paid"))
                and self.env.context.get("_bank_slip_register_batch") is not _REGISTER_BATCH):
            for payment in self:
                registry.claim(payment, payment.bank_reference)
        return result
