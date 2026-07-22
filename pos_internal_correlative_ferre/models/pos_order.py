# -*- coding: utf-8 -*-
import random
import time

from psycopg2 import OperationalError

from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    internal_correlative = fields.Char(
        string="Correlativo interno",
        index=True,
        copy=False,
    )

    def _next_correlative_for_session(self, session_id, invoiced=False):
        """Return the next sequence configured for the POS session."""
        if not session_id:
            return False
        session = self.env["pos.session"].browse(session_id).exists()
        if not session or not session.config_id:
            return False

        config = session.config_id.sudo()
        config._ensure_internal_sequence()
        sequence = (
            config.pos_internal_sequence_id
            if invoiced
            else config.pos_internal_sequence_no_invoice_id
        )
        sequence = sequence or (
            config.pos_internal_sequence_no_invoice_id
            if invoiced
            else config.pos_internal_sequence_id
        )
        if not sequence:
            return False

        for attempt in range(5):
            try:
                with self.env.cr.savepoint():
                    return sequence.sudo().next_by_id()
            except OperationalError as exc:
                message = str(exc).lower()
                if "could not obtain lock" not in message and "lock not available" not in message:
                    raise
                if attempt < 4:
                    time.sleep(0.15 + random.random() * 0.25)
        return sequence.sudo().next_by_id()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("internal_correlative"):
                continue
            invoiced = bool(vals.get("to_invoice") or vals.get("is_invoiced"))
            correlative = self._next_correlative_for_session(
                vals.get("session_id"), invoiced=invoiced
            )
            if not correlative:
                correlative = self.env["ir.sequence"].sudo().next_by_code(
                    "pos.internal.correlative"
                )
            if correlative:
                vals["internal_correlative"] = correlative
        return super().create(vals_list)

    def _prepare_invoice_vals(self):
        """Copy the POS number while the invoice values are being prepared.

        This is more reliable than trying to discover the relation after the
        account.move has already been created.
        """
        self.ensure_one()
        vals = super()._prepare_invoice_vals()
        if self.internal_correlative:
            vals["internal_correlative"] = self.internal_correlative
        return vals

    def _sync_internal_correlative_to_invoice(self):
        for order in self.filtered("internal_correlative"):
            move = order.account_move
            if move and move.internal_correlative != order.internal_correlative:
                move.sudo().write({"internal_correlative": order.internal_correlative})

    def _generate_pos_order_invoice(self):
        result = super()._generate_pos_order_invoice()
        self._sync_internal_correlative_to_invoice()
        return result
