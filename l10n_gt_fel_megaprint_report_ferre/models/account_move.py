# -*- coding: utf-8 -*-
from math import modf

from odoo import api, fields, models

try:
    from num2words import num2words
except Exception:
    num2words = None


class AccountMove(models.Model):
    _inherit = "account.move"

    firma_fel = fields.Char(string="Firma FEL / No. Autorización")
    serie_fel = fields.Char(string="Serie FEL")
    numero_fel = fields.Char(string="Número DTE")

    amount_total_gt_words = fields.Char(
        string="Total en letras (GT)",
        compute="_compute_amount_total_gt_words",
        store=False,
    )

    @api.depends("amount_total", "currency_id")
    def _compute_amount_total_gt_words(self):
        for move in self:
            amount = move.amount_total or 0.0
            frac, entero = modf(amount)
            quetzales = int(entero)
            centavos = int(round(frac * 100.0))
            if centavos == 100:
                quetzales += 1
                centavos = 0

            texto_entero = num2words(quetzales, lang="es") if num2words else str(quetzales)
            moneda = "QUETZALES" if quetzales != 1 else "QUETZAL"
            move.amount_total_gt_words = (
                f"{texto_entero} {moneda} CON {centavos:02d}/100"
            ).upper()

    def _get_related_pos_order(self):
        """Return the POS order linked to this invoice, without custom fields.

        The previous implementation tried to read ``stock_location_name`` from
        ``pos.order.line``. That field belonged to an old multi-warehouse POS
        customization and is not present in the current one-POS/one-warehouse
        architecture.
        """
        self.ensure_one()
        PosOrder = self.env["pos.order"].sudo()

        if "account_move" in PosOrder._fields:
            order = PosOrder.search([("account_move", "=", self.id)], limit=1)
            if order:
                return order

        if "pos_order_ids" in self._fields and self.pos_order_ids:
            return self.pos_order_ids[:1]

        origins = [
            value
            for value in (self.invoice_origin, self.ref, self.payment_reference)
            if value
        ]
        if origins and "name" in PosOrder._fields:
            order = PosOrder.search([("name", "in", origins)], limit=1)
            if order:
                return order

        return PosOrder.browse()

    def _warehouse_label_from_pos_order(self, order):
        """Resolve the fixed warehouse configured for the POS order."""
        self.ensure_one()
        if not order:
            return ""

        config = getattr(order, "config_id", False)
        picking_type = getattr(config, "picking_type_id", False) if config else False
        warehouse = getattr(picking_type, "warehouse_id", False) if picking_type else False
        if warehouse:
            return warehouse.display_name or warehouse.name or ""

        source_location = (
            getattr(picking_type, "default_location_src_id", False)
            if picking_type
            else False
        )
        if source_location:
            return source_location.complete_name or source_location.display_name or ""

        pickings = getattr(order, "picking_ids", False)
        if pickings:
            picking = pickings[:1]
            warehouse = getattr(picking.picking_type_id, "warehouse_id", False)
            if warehouse:
                return warehouse.display_name or warehouse.name or ""
            if picking.location_id:
                return picking.location_id.complete_name or picking.location_id.display_name or ""

        return ""

    def _warehouse_label_from_sale_line(self, line):
        """Fallback for invoices created from a regular sales order."""
        self.ensure_one()
        if "sale_line_ids" not in line._fields or not line.sale_line_ids:
            return ""
        orders = line.sale_line_ids.mapped("order_id")
        warehouses = orders.mapped("warehouse_id") if orders else self.env["stock.warehouse"]
        warehouse = warehouses[:1]
        return warehouse.display_name or warehouse.name or "" if warehouse else ""

    def get_wh_for_line(self, line):
        """Return a warehouse label without relying on old multiwarehouse fields.

        In the current design each POS has one fixed picking type and therefore
        one warehouse. All invoice lines from that POS use that warehouse.
        Missing warehouse information must never block FEL PDF rendering.
        """
        self.ensure_one()
        try:
            order = self._get_related_pos_order()
            label = self._warehouse_label_from_pos_order(order)
            if label:
                return label
        except Exception:
            # Reporting must remain non-blocking; use the SO fallback or blank.
            pass

        try:
            return self._warehouse_label_from_sale_line(line)
        except Exception:
            return ""
