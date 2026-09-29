import re

from odoo import api, fields, models


NIT_SEPARATOR_RE = re.compile(r"[-\s]+")


def normalize_nit(value):
    """Normalize a NIT only for comparison, without changing ``res.partner.vat``."""
    return NIT_SEPARATOR_RE.sub("", value or "").casefold()


class ResPartner(models.Model):
    _inherit = "res.partner"

    pos_nit_search_normalized = fields.Char(
        string="NIT normalizado para búsqueda POS",
        compute="_compute_pos_nit_search_normalized",
        search="_search_pos_nit_search_normalized",
        help="Campo técnico no almacenado; elimina guiones y espacios solo al comparar.",
    )

    @api.depends("vat")
    def _compute_pos_nit_search_normalized(self):
        for partner in self:
            partner.pos_nit_search_normalized = normalize_nit(partner.vat)

    @api.model
    def _search_pos_nit_search_normalized(self, operator, value):
        if operator not in ("=", "==", "ilike", "=ilike"):
            return [("id", "=", 0)]

        normalized_value = normalize_nit(value)
        if not normalized_value:
            return [("id", "=", 0)]

        # VAT is prefiltered in SQL; normalization and exact comparison happen in
        # Python because PostgreSQL domains cannot strip both separators safely.
        candidates = self.search([("vat", "!=", False)])
        matching_ids = [
            partner.id
            for partner in candidates
            if normalize_nit(partner.vat) == normalized_value
        ]
        return [("id", "in", matching_ids)]

