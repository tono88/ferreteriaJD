# -*- coding: utf-8 -*-
import re
from collections import OrderedDict

import pytz

from odoo import api, fields, models, _


class ReportPosSalesSummary(models.AbstractModel):
    _name = "report.pos_sales_summary_report_ferre.report_pos_sales_summary"
    _description = "Reporte PDF: Resumen de ventas POS"

    @staticmethod
    def _has_valid_invoice(order):
        move = getattr(order, "account_move", False)
        return bool(move and move.state == "posted")

    def _normalize_pos_config_id(self, data):
        if not data:
            return None
        value = data.get("pos_config_id")
        if not value and isinstance(data.get("form"), dict):
            value = data["form"].get("pos_config_id")
        if isinstance(value, (list, tuple)):
            value = value[0]
        return int(value) if value else None

    @staticmethod
    def _is_cash_method(method):
        if not method:
            return False
        if getattr(method, "is_cash_count", False):
            return True
        journal = getattr(method, "journal_id", False)
        if journal and getattr(journal, "is_cash_count", False):
            return True
        method_type = getattr(method, "type", None)
        return isinstance(method_type, str) and method_type.lower() == "cash"

    def _split_payments(self, order):
        cash = 0.0
        other = 0.0
        for payment in order.payment_ids:
            amount = payment.amount or 0.0
            if amount <= 0:
                continue
            if self._is_cash_method(payment.payment_method_id):
                cash += amount
            else:
                other += amount
        return cash, other

    @staticmethod
    def _format_amount(amount, currency):
        text = "{:,.2f}".format(amount or 0.0)
        if not currency:
            return text
        if currency.position == "before":
            return f"{currency.symbol} {text}"
        return f"{text} {currency.symbol}"

    def _report_timezone(self):
        timezone_name = (
            self.env.user.tz
            or self.env.company.partner_id.tz
            or "America/Guatemala"
        )
        try:
            pytz.timezone(timezone_name)
        except pytz.UnknownTimeZoneError:
            timezone_name = "America/Guatemala"
        return timezone_name

    def _order_local_date(self, order):
        if not order.date_order:
            return False
        localized = fields.Datetime.context_timestamp(
            order.with_context(tz=self._report_timezone()), order.date_order
        )
        return localized.date()

    def _document_date_data(self, order):
        move = order.account_move
        if move and move.state == "posted" and move.invoice_date:
            return move.invoice_date, ""

        fallback_date = self._order_local_date(order)
        if not move and order.state == "invoiced":
            observation = _("Orden facturada sin factura vinculada")
        elif move and move.state == "cancel":
            observation = _("Factura cancelada")
        elif move and move.state == "draft":
            observation = _("Factura en borrador")
        elif move and move.state == "posted" and not move.invoice_date:
            observation = _("Factura publicada sin fecha")
        elif move and move.state not in ("posted", "draft", "cancel"):
            observation = _("Estado de factura: %s") % move.state
        else:
            observation = ""
        return fallback_date, observation

    def _line_from_order(self, order, currency):
        move = order.account_move
        invoice = "-"
        if move:
            invoice = getattr(move, "firma_fel", False) or move.name or "-"

        document_date, observation = self._document_date_data(order)
        cash, other = self._split_payments(order)
        total = order.amount_total or 0.0
        return {
            "partner": order.partner_id.name or _("Consumidor Final"),
            "correlative": order.internal_correlative or "-",
            "invoice": invoice,
            "document_date": document_date,
            "document_date_label": document_date.strftime("%d/%m/%Y") if document_date else "-",
            "observation": observation,
            "contado": cash,
            "credito": other,
            "total": total,
            "contado_fmt": self._format_amount(cash, currency),
            "credito_fmt": self._format_amount(other, currency),
            "total_fmt": self._format_amount(total, currency),
            "order_name": order.name,
        }

    @staticmethod
    def _correlative_key(line):
        value = (line.get("correlative") or "").strip()
        match = re.match(r"^(.*?)(\d+)$", value)
        if match:
            return (match.group(1).casefold(), int(match.group(2)), value.casefold())
        return (value.casefold(), -1, value.casefold())

    def _search_orders(self, data):
        start_utc = data.get("start_utc")
        end_utc = data.get("end_utc")
        invoice_filter = data.get("invoice_filter", "all")
        pos_config_id = self._normalize_pos_config_id(data)
        partner_ids = data.get("partner_ids") or []
        if isinstance(partner_ids, int):
            partner_ids = [partner_ids]

        domain = [
            ("state", "in", ["paid", "done", "invoiced"]),
            ("date_order", ">=", start_utc),
            ("date_order", "<=", end_utc),
        ]
        if pos_config_id:
            domain += [
                "|",
                ("config_id", "=", pos_config_id),
                ("session_id.config_id", "=", pos_config_id),
            ]
        if partner_ids:
            domain.append(("partner_id", "in", partner_ids))

        orders = self.env["pos.order"].search(
            domain, order="partner_id, date_order, name"
        )

        # Preserve the existing business rule: if a refund order explicitly
        # names its origin, show the refund and omit the original in the range.
        refund_domain = [
            ("state", "in", ["paid", "done", "invoiced"]),
            ("date_order", ">=", start_utc),
            ("date_order", "<=", end_utc),
            ("amount_total", "<", 0),
        ]
        if pos_config_id:
            refund_domain += [
                "|",
                ("config_id", "=", pos_config_id),
                ("session_id.config_id", "=", pos_config_id),
            ]
        if partner_ids:
            refund_domain.append(("partner_id", "in", partner_ids))
        refund_orders = self.env["pos.order"].search(refund_domain)
        original_names = set()
        for refund in refund_orders:
            name = (refund.name or "").strip()
            if name.upper().startswith("REEMBOLSO DE "):
                original_names.add(name[len("REEMBOLSO DE "):].strip())
        if original_names:
            orders = orders.filtered(lambda order: order.name not in original_names)

        if invoice_filter == "invoiced":
            orders = orders.filtered(self._has_valid_invoice)
        elif invoice_filter == "not_invoiced":
            orders = orders.filtered(lambda order: not self._has_valid_invoice(order))
        return orders

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        orders = self._search_orders(data)
        currency = self.env.company.currency_id
        lines = []
        invoice_references = []
        for order in orders:
            line = self._line_from_order(order, currency)
            if line["contado"] == 0 and line["credito"] == 0:
                continue
            lines.append(line)
            if line["invoice"] != "-":
                invoice_references.append(line["invoice"])

        order_by_correlative = bool(data.get("order_by_internal_correlative"))
        lines_linear = (
            sorted(lines, key=self._correlative_key)
            if order_by_correlative
            else list(lines)
        )

        grouped = OrderedDict()
        for line in lines:
            grouped.setdefault(line["partner"], []).append(line)
        grouped_list = [
            {"partner": partner, "lines": partner_lines}
            for partner, partner_lines in sorted(
                grouped.items(), key=lambda item: (item[0] or "").casefold()
            )
        ]

        total_cash = sum(line["contado"] for line in lines)
        total_other = sum(line["credito"] for line in lines)
        total_general = sum(line["total"] for line in lines)
        now = fields.Datetime.context_timestamp(self.env.user, fields.Datetime.now())

        return {
            "doc_ids": docids,
            "doc_model": "pos.order",
            "data": data,
            "grouped": grouped_list,
            "lines_linear": lines_linear,
            "order_by_internal_correlative": order_by_correlative,
            "total_contado": total_cash,
            "total_credito": total_other,
            "total_general": total_general,
            "total_contado_fmt": self._format_amount(total_cash, currency),
            "total_credito_fmt": self._format_amount(total_other, currency),
            "total_general_fmt": self._format_amount(total_general, currency),
            "first_invoice": invoice_references[0] if invoice_references else "-",
            "last_invoice": invoice_references[-1] if invoice_references else "-",
            "user_label": self.env.user.name,
            "now_label": now.strftime("%d/%m/%Y %I:%M:%S %p"),
            "company": self.env.company,
            "report_timezone": self._report_timezone(),
        }
