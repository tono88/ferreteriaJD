# -*- coding: utf-8 -*-

from odoo import models


class PosConfig(models.Model):
    _inherit = "pos.config"

    def _ferreteria_transfer_warehouse(self):
        """Return the warehouse configured by the POS operation type.

        In Odoo 18 the visible POS setting is ``picking_type_id`` (Operation
        Type).  Its ``warehouse_id`` is therefore the authoritative branch for
        transfer requests.  ``pos.config.warehouse_id`` is only used as a safe
        fallback for unusual/custom operation types without a warehouse.
        """
        self.ensure_one()
        return self.picking_type_id.warehouse_id or self.warehouse_id
