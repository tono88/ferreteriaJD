# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PosOrderPaymentMaster(models.Model):
    _inherit = "pos.order.payment.master"

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
        masters = super().create(vals_list)
        for master in masters:
            registry.claim(master, master.bank_slip_number)
        return masters

    def write(self, vals):
        registry = self.env["ferreteria.bank.slip.registry"]
        if "bank_slip_number" in vals:
            vals["bank_slip_number"] = registry.clean_number(vals.get("bank_slip_number"))
        result = super().write(vals)
        if "bank_slip_number" in vals:
            for master in self:
                registry.claim(master, master.bank_slip_number)
        return result
