# -*- coding: utf-8 -*-
from odoo import fields, models
from .account_payment import _REGISTER_BATCH


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def _create_payments(self):
        self.ensure_one()
        # The accounting kit writes bank_reference after super creates/posts
        # the payments. Defer through the entire chain, not just create().
        wizard = self.with_context(_bank_slip_register_batch=_REGISTER_BATCH)
        with self.env.cr.savepoint():
            payments = super(AccountPaymentRegister, wizard)._create_payments()
            # Remove the marker from the returned recordset so future edits
            # always enforce uniqueness normally.
            payments = payments.with_env(self.env)
            self.env["ferreteria.bank.slip.registry"]._claim_payment_batch(payments)
        return payments


class PosOrderPaymentWizard(models.TransientModel):
    _inherit = "pos.order.payment.wizard"

    bank_slip_number = fields.Char(string="No. boleta bancaria")

    def action_confirm(self):
        self.ensure_one()
        wizard = self.with_context(default_bank_slip_number=self.bank_slip_number)
        return super(PosOrderPaymentWizard, wizard).action_confirm()


class PosOrderPaymentMasterWizard(models.TransientModel):
    _inherit = "pos.order.payment.master.wizard"

    bank_slip_number = fields.Char(string="No. boleta bancaria")

    def action_confirm(self):
        self.ensure_one()
        result = super().action_confirm()
        master_id = result.get("res_id") if isinstance(result, dict) else False
        if master_id and self.bank_slip_number:
            self.env["pos.order.payment.master"].browse(master_id).write(
                {"bank_slip_number": self.bank_slip_number}
            )
        return result
