# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import AccessError, ValidationError
from .account_payment import _REGISTER_BATCH


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    recover_bank_slip = fields.Boolean(string="Recuperar boleta anulada")
    bank_slip_recovery_reason = fields.Char(string="Motivo de recuperación")

    def action_create_payments(self):
        # The legacy checker also intercepts the public button, and considers
        # Odoo 18's 'canceled' records duplicates (it tests the old 'cancel').
        # The historical registry below remains authoritative on every path.
        wizard = self.with_context(skip_bank_reference_dup_check=True)
        return super(AccountPaymentRegister, wizard).action_create_payments()

    def _create_payments(self):
        self.ensure_one()
        reason = None
        if self.recover_bank_slip:
            if not (self.env.user.has_group("account.group_account_manager")
                    or self.env.user.has_group("base.group_system")):
                raise AccessError(_("Solo un administrador contable puede recuperar una boleta."))
            reason = (self.bank_slip_recovery_reason or "").strip()
            if not reason or not self.bank_reference:
                raise ValidationError(_("Indique la boleta y el motivo de recuperación."))
        # The accounting kit writes bank_reference after super creates/posts
        # the payments. Defer through the entire chain, not just create().
        wizard = self.with_context(_bank_slip_register_batch=_REGISTER_BATCH)
        with self.env.cr.savepoint():
            payments = super(AccountPaymentRegister, wizard)._create_payments()
            if any(p.move_id and p.move_id.state != "posted" for p in payments):
                raise ValidationError(_(
                    "No se contabilizaron todos los asientos de pago. "
                    "La operación se revirtió para evitar pagos sin aplicar."
                ))
            # Remove the marker from the returned recordset so future edits
            # always enforce uniqueness normally.
            payments = payments.with_env(self.env)
            self.env["ferreteria.bank.slip.registry"]._claim_payment_batch(payments, reason)
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
