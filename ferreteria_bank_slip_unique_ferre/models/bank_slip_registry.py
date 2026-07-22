# -*- coding: utf-8 -*-
import unicodedata

from psycopg2 import IntegrityError

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class FerreteriaBankSlipRegistry(models.Model):
    _name = "ferreteria.bank.slip.registry"
    _description = "Registro histórico de boletas bancarias"
    _order = "create_date desc, id desc"

    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        index=True,
        ondelete="restrict",
    )
    number_original = fields.Char(
        string="Número registrado",
        required=True,
        readonly=True,
    )
    number_normalized = fields.Char(
        string="Número normalizado",
        required=True,
        readonly=True,
        index=True,
    )
    source_model = fields.Char(string="Modelo origen", required=True, readonly=True, index=True)
    source_res_id = fields.Integer(string="ID origen", required=True, readonly=True, index=True)
    source_display_name = fields.Char(string="Pago origen", required=True, readonly=True)
    registered_by_id = fields.Many2one(
        "res.users",
        string="Registrado por",
        default=lambda self: self.env.user,
        required=True,
        readonly=True,
    )

    _sql_constraints = [
        (
            "bank_slip_company_number_unique",
            "unique(company_id, number_normalized)",
            "El número de boleta bancaria ya fue utilizado en esta compañía.",
        ),
    ]

    @api.model
    def normalize_number(self, value):
        if not value:
            return ""
        return unicodedata.normalize("NFKC", str(value).strip()).casefold()

    @api.model
    def clean_number(self, value):
        return unicodedata.normalize("NFKC", str(value).strip()) if value else ""

    @api.model
    def _duplicate_message(self, normalized, company):
        duplicate = self.sudo().search(
            [
                ("company_id", "=", company.id),
                ("number_normalized", "=", normalized),
            ],
            limit=1,
        )
        if duplicate:
            return _(
                "La boleta bancaria %(number)s ya fue utilizada en %(payment)s. "
                "No es posible registrarla nuevamente."
            ) % {
                "number": duplicate.number_original,
                "payment": duplicate.source_display_name,
            }
        return _("La boleta bancaria ya fue utilizada en esta compañía.")

    @api.model
    def _source_label(self, source):
        source.ensure_one()
        if source._name == "account.payment":
            partner = source.partner_id.display_name if source.partner_id else _("Sin tercero")
            return _("Pago %(payment)s — %(partner)s") % {
                "payment": source.display_name,
                "partner": partner,
            }
        if source._name == "pos.order.payment":
            return _("Pago POS de %(order)s") % {
                "order": source.pos_order_id.display_name,
            }
        if source._name == "pos.order.payment.master":
            return _("Pago maestro POS %(payment)s") % {
                "payment": source.display_name,
            }
        return source.display_name or f"{source._name},{source.id}"

    @api.model
    def claim(self, source, number):
        """Reserve a bank-slip number permanently for a source payment.

        Historical claims are intentionally retained if a payment is later
        cancelled, deleted or edited, implementing the strict no-reuse policy.
        """
        source.ensure_one()
        cleaned = self.clean_number(number)
        normalized = self.normalize_number(cleaned)
        if not normalized:
            return cleaned

        company = getattr(source, "company_id", False) or self.env.company
        same_claim = self.sudo().search(
            [
                ("company_id", "=", company.id),
                ("number_normalized", "=", normalized),
                ("source_model", "=", source._name),
                ("source_res_id", "=", source.id),
            ],
            limit=1,
        )
        if same_claim:
            return cleaned

        values = {
            "company_id": company.id,
            "number_original": cleaned,
            "number_normalized": normalized,
            "source_model": source._name,
            "source_res_id": source.id,
            "source_display_name": self._source_label(source),
            "registered_by_id": self.env.user.id,
        }
        try:
            with self.env.cr.savepoint():
                self.sudo().create(values)
        except IntegrityError:
            raise ValidationError(self._duplicate_message(normalized, company)) from None
        return cleaned
