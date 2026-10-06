# -*- coding: utf-8 -*-

from odoo import models


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _build_wkhtmltopdf_args(
        self,
        paperformat_id,
        landscape,
        specific_paperformat_args=None,
        set_viewport_size=False,
    ):
        args = super()._build_wkhtmltopdf_args(
            paperformat_id,
            landscape,
            specific_paperformat_args=specific_paperformat_args,
            set_viewport_size=set_viewport_size,
        )
        thermal_format = self.env.ref(
            "ferreteria_pos_fel_ticket.paperformat_pos_fel_ticket_80mm",
            raise_if_not_found=False,
        )
        if thermal_format and paperformat_id == thermal_format and "--encoding" not in args:
            args.extend(["--encoding", "utf-8"])
        return args
