# -*- coding: utf-8 -*-
from odoo import _, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def _ferreteria_has_direct_storable_lines(self):
        self.ensure_one()
        for line in self.invoice_line_ids.filtered(lambda item: not item.display_type):
            product = line.product_id
            is_storable = bool(
                product
                and (
                    getattr(product, "is_storable", False)
                    or getattr(product, "type", False) == "product"
                )
            )
            if is_storable and line.quantity > 0:
                return True
        return False

    def _ferreteria_has_inventory_origin(self):
        self.ensure_one()
        if "pos_order_ids" in self._fields and self.pos_order_ids:
            return True
        return any(
            "sale_line_ids" in line._fields and line.sale_line_ids
            for line in self.invoice_line_ids
        )

    def _post(self, soft=True):
        for move in self:
            if (
                move.move_type == "out_invoice"
                and move._ferreteria_has_direct_storable_lines()
                and not move._ferreteria_has_inventory_origin()
            ):
                raise UserError(
                    _(
                        "No se puede publicar una factura directa con productos "
                        "almacenables porque no existe un almacén de origen que permita "
                        "validar y descontar el inventario. Registre la operación desde "
                        "Ventas o desde el Punto de Venta."
                    )
                )
        return super()._post(soft=soft)
