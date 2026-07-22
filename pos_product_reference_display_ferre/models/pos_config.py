# Copyright 2026 - Distribuidora y Ferretería JB implementation
# Inspired by OCA/pos pos_product_display_default_code.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class PosConfig(models.Model):
    _inherit = "pos.config"

    def get_limited_products_loading(self, fields):
        """Include the internal reference in product display names.

        Odoo uses this path when limited product loading is enabled.  The
        context only affects the display name returned to the POS; it does not
        alter product names or references in the database.
        """
        self = self.with_context(display_default_code=True)
        return super().get_limited_products_loading(fields)
