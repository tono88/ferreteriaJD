# Copyright 2026 - Distribuidora y Ferretería JB implementation
# Inspired by OCA/pos pos_product_display_default_code.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _load_product_with_domain(self, domain, config_id, load_archived=False):
        """Load POS products with ``[default_code] name`` as display name.

        The standard Odoo method forces ``display_default_code=False``.  This
        small override keeps the same fields, domain, archive handling and
        ordering, changing only that context value.
        """
        fields = self._load_pos_data_fields(config_id)
        context = {
            **self.env.context,
            "display_default_code": True,
            "active_test": not load_archived,
            "bin_size": True,
        }
        return self.with_context(context).search_read(
            domain,
            fields,
            order="sequence,default_code,name",
            load=False,
        )
