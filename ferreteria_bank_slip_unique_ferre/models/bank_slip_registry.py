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
    payment_ids = fields.Many2many(
        "account.payment",
        "ferre_bank_slip_account_payment_rel",
        "registry_id", "payment_id",
        string="Pagos de la operación", readonly=True, copy=False,
    )
    recovery_history = fields.Json(string="Historial de recuperaciones", readonly=True, copy=False)
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
        """Reserve a number for an active payment; cancelled payments do not count."""
        source.ensure_one()
        cleaned = self.clean_number(number)
        normalized = self.normalize_number(cleaned)
        if not normalized:
            return cleaned
        if source._name == "account.payment" and source.state == "canceled":
            return cleaned

        company = getattr(source, "company_id", False) or self.env.company
        # Normal posting/editing must serialize with administrative recovery as
        # well, so an old payment cannot reactivate while its claim is replaced.
        self.env.cr.execute(
            "SELECT id FROM ferreteria_bank_slip_registry "
            "WHERE company_id = %s AND number_normalized = %s FOR UPDATE",
            [company.id, normalized],
        )
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

        if source._name == "account.payment" and self.sudo().search_count([
            ("company_id", "=", company.id),
            ("number_normalized", "=", normalized),
            ("payment_ids", "in", source.ids),
        ]):
            return cleaned

        existing = self.sudo().search([
            ("company_id", "=", company.id),
            ("number_normalized", "=", normalized),
        ], limit=1)
        if source._name == "account.payment" and self._is_cancelled_claim(existing):
            self._recover_cancelled_claim(existing, source)
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

    @api.model
    def _claim_payment_batch(self, payments):
        """Reserve each number for payments created by ONE register operation.

        Private: accepting arbitrary existing payments here via RPC would let
        users attach unrelated payments to an already reserved bank slip.
        The wizard calls this inside its savepoint after all inherited writes.
        """
        groups = {}
        for payment in payments:
            normalized = self.normalize_number(payment.bank_reference)
            if normalized:
                key = (payment.company_id.id, normalized)
                groups.setdefault(key, self.env["account.payment"])
                groups[key] |= payment
        for (company_id, normalized), batch in groups.items():
            existing = self.sudo().search([
                ("company_id", "=", company_id),
                ("number_normalized", "=", normalized),
            ], limit=1)
            if self._is_cancelled_claim(existing):
                self._recover_cancelled_claim(existing, batch)
                continue
            self.claim(batch[0], batch[0].bank_reference)
            claim = self.sudo().search([
                ("company_id", "=", company_id),
                ("number_normalized", "=", normalized),
            ], limit=1)
            claim.write({"payment_ids": [(4, payment.id) for payment in batch]})

    @api.model
    def _is_cancelled_claim(self, claim):
        if not claim or claim.source_model != "account.payment":
            return False
        Payment = self.env["account.payment"].sudo().with_context(active_test=False)
        previous = claim.payment_ids | Payment.browse(claim.source_res_id).exists()
        return all(payment.state == "canceled" for payment in previous)

    @api.model
    def _recover_cancelled_claim(self, claim, payments):
        """Automatically replace a cancelled/deleted accounting operation.

        Private and called only by the normal claim path, under the same row
        lock. Keep the old reservation in the audit trail without extra UI.
        """
        # Serialize recoveries of the same reservation. The unique SQL constraint
        # is kept intact; a reservation is never deleted or temporarily released.
        self.env.cr.execute(
            "SELECT id FROM ferreteria_bank_slip_registry WHERE id = %s FOR UPDATE",
            [claim.id],
        )
        claim.invalidate_recordset()
        if claim.source_model != "account.payment":
            raise ValidationError(_("No se puede recuperar una boleta reservada por pagos POS."))
        Payment = self.env["account.payment"].sudo().with_context(active_test=False)
        previous = claim.payment_ids | Payment.browse(claim.source_res_id).exists()
        previous.invalidate_recordset()
        if any(payment.state != "canceled" for payment in previous):
            raise ValidationError(_("La boleta todavía tiene pagos sin cancelar; no se puede recuperar."))
        # Also detect manually edited/unlinked associations, with identical Unicode
        # normalization to the reservation itself (not only an exact SQL match).
        others = Payment.search([
            ("company_id", "=", claim.company_id.id),
            ("bank_reference", "!=", False),
            ("state", "!=", "canceled"),
            ("id", "not in", payments.ids),
        ])
        if any(self.normalize_number(p.bank_reference) == claim.number_normalized for p in others):
            raise ValidationError(_("La boleta todavía está en uso por otro pago activo."))
        snapshot = {
            "source_model": claim.source_model,
            "source_res_id": claim.source_res_id,
            "source_display_name": claim.source_display_name,
            "payment_ids": previous.ids,
            "registered_by_id": claim.registered_by_id.id,
            "registered_on": fields.Datetime.to_string(claim.create_date),
            "recovered_by_id": self.env.uid,
            "recovered_on": fields.Datetime.to_string(fields.Datetime.now()),
            "reason": "Reutilización automática: los pagos anteriores están cancelados o eliminados.",
            "replacement_payment_ids": payments.ids,
        }
        claim.write({
            "recovery_history": (claim.recovery_history or []) + [snapshot],
            "source_model": "account.payment",
            "source_res_id": payments[0].id,
            "source_display_name": self._source_label(payments[0]),
            "payment_ids": [(6, 0, payments.ids)],
        })
