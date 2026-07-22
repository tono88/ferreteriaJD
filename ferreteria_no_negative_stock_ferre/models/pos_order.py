# -*- coding: utf-8 -*-
from odoo import _, models
from odoo.exceptions import UserError

from .stock_guard import validate_stock_requirements


class PosOrder(models.Model):
    _inherit = "pos.order"

    def _ferreteria_get_pos_warehouse(self):
        self.ensure_one()
        config = self.config_id or self.session_id.config_id
        picking_type = config.picking_type_id
        warehouse = picking_type.warehouse_id
        if not warehouse:
            raise UserError(
                _(
                    "El punto de venta %(pos)s no tiene un almacén asociado mediante "
                    "su tipo de operación. Configure POS → Tipo de operación → Almacén."
                )
                % {"pos": config.display_name}
            )
        return warehouse

    def _ferreteria_pos_stock_requirements(self):
        self.ensure_one()
        requirements = []
        for line in self.lines:
            product = line.product_id
            quantity = line.qty
            line_uom = (
                line.product_uom_id
                if "product_uom_id" in line._fields and line.product_uom_id
                else product.uom_id
            )
            quantity_product_uom = line_uom._compute_quantity(
                quantity,
                product.uom_id,
            )
            requirements.append((product, quantity_product_uom))
        return requirements

    def _ferreteria_validate_pos_stock(self):
        for order in self:
            if order.state == "cancel":
                continue
            warehouse = order._ferreteria_get_pos_warehouse()
            validate_stock_requirements(
                order.env,
                location=warehouse.lot_stock_id,
                requirements=order._ferreteria_pos_stock_requirements(),
                warehouse_name=warehouse.display_name,
            )
        return True

    def _force_create_picking_real_time(self):
        """Always reflect POS sales in stock immediately.

        A deferred picking at session closing would leave no reservation after
        validation and would allow another terminal to reuse the same stock.
        """
        return True

    def _create_order_picking(self):
        self.ensure_one()
        if not self.picking_ids:
            self._ferreteria_validate_pos_stock()
        return super()._create_order_picking()
