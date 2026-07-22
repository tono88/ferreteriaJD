# -*- coding: utf-8 -*-
from odoo import models

from .stock_guard import validate_stock_requirements


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _ferreteria_sale_stock_requirements(self):
        self.ensure_one()
        requirements = []
        for line in self.order_line.filtered(lambda item: not item.display_type):
            product = line.product_id
            quantity_product_uom = line.product_uom._compute_quantity(
                line.product_uom_qty,
                product.uom_id,
            )
            requirements.append((product, quantity_product_uom))
        return requirements

    def action_confirm(self):
        for order in self:
            warehouse = order.warehouse_id
            validate_stock_requirements(
                order.env,
                location=warehouse.lot_stock_id,
                requirements=order._ferreteria_sale_stock_requirements(),
                warehouse_name=warehouse.display_name,
            )
        return super().action_confirm()
