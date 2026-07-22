# -*- coding: utf-8 -*-
from odoo import fields, models


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
