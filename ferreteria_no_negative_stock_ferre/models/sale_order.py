# -*- coding: utf-8 -*-
"""Control de stock para Ventas, compatible con cobros de cotizaciones en POS."""
from odoo import models
from odoo.tools.float_utils import float_compare

from .stock_guard import validate_stock_requirements


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _ferreteria_sale_stock_requirements(self):
        self.ensure_one()
        requirements = []
        for line in self.order_line.filtered(lambda item: not item.display_type):
            product = line.product_id
            quantity_product_uom = line.product_uom._compute_quantity(
                line.product_uom_qty, product.uom_id,
            )

            # pos_sale vincula la orden de venta y la línea POS con
            # sale_order_line_id. Si POS YA ENTREGÓ físicamente el producto,
            # no se puede volver a exigir esa cantidad de stock libre durante
            # action_confirm(): POS descontó el inventario antes de confirmar SO.
            # Nunca se descuentan cantidades de órdenes sin pagar, sin picking
            # terminado, de otra compañía, de otro almacén o sin vínculo real.
            processed_qty = 0.0
            if "pos_order_line_ids" in line._fields:
                for pos_line in line.pos_order_line_ids:
                    pos = pos_line.order_id
                    if pos.state not in ("paid", "done", "invoiced"):
                        continue
                    if pos.company_id != self.company_id:
                        continue
                    if pos.config_id.picking_type_id.warehouse_id != self.warehouse_id:
                        continue
                    if not pos.picking_ids or not all(
                        picking.state == "done" for picking in pos.picking_ids
                    ):
                        continue
                    # Unidades de la línea POS a UDM del producto.
                    pos_uom = (
                        pos_line.product_uom_id
                        if "product_uom_id" in pos_line._fields
                        and pos_line.product_uom_id
                        else product.uom_id
                    )
                    processed_qty += pos_uom._compute_quantity(
                        pos_line.qty, product.uom_id
                    )
            remaining = max(quantity_product_uom - processed_qty, 0.0)
            if float_compare(
                remaining, 0.0, precision_rounding=product.uom_id.rounding
            ) > 0:
                requirements.append((product, remaining))
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
