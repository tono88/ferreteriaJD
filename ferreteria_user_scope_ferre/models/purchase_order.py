from odoo import _, api, models
from odoo.exceptions import AccessError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.model
    def _ferreteria_check_picking_type_scope(self, picking_type):
        user = self.env.user
        if not user.ferreteria_scope_enforced or self.env.su:
            return
        warehouse = picking_type.warehouse_id
        if not warehouse or warehouse not in user.ferreteria_allowed_warehouse_ids:
            raise AccessError(
                _("No puede operar compras destinadas a un almacén fuera de su ámbito Ferretería.")
            )

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.user.ferreteria_scope_enforced and not self.env.su:
            default_picking_type = self.default_get(["picking_type_id"]).get("picking_type_id")
            for vals in vals_list:
                picking_type_id = vals.get("picking_type_id") or default_picking_type
                self._ferreteria_check_picking_type_scope(
                    self.env["stock.picking.type"].browse(picking_type_id)
                )
        orders = super().create(vals_list)
        for order in orders:
            self._ferreteria_check_picking_type_scope(order.picking_type_id)
        return orders

    def write(self, vals):
        if "picking_type_id" in vals:
            self._ferreteria_check_picking_type_scope(
                self.env["stock.picking.type"].browse(vals["picking_type_id"])
            )
        result = super().write(vals)
        for order in self:
            self._ferreteria_check_picking_type_scope(order.picking_type_id)
        return result

    def button_confirm(self):
        for order in self:
            self._ferreteria_check_picking_type_scope(order.picking_type_id)
        return super().button_confirm()


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.user.ferreteria_scope_enforced and not self.env.su:
            for vals in vals_list:
                order = self.env["purchase.order"].browse(vals.get("order_id"))
                self.env["purchase.order"]._ferreteria_check_picking_type_scope(
                    order.picking_type_id
                )
        lines = super().create(vals_list)
        for order in lines.mapped("order_id"):
            self.env["purchase.order"]._ferreteria_check_picking_type_scope(
                order.picking_type_id
            )
        return lines

    def write(self, vals):
        if "order_id" in vals:
            order = self.env["purchase.order"].browse(vals["order_id"])
            self.env["purchase.order"]._ferreteria_check_picking_type_scope(
                order.picking_type_id
            )
        result = super().write(vals)
        for order in self.mapped("order_id"):
            self.env["purchase.order"]._ferreteria_check_picking_type_scope(
                order.picking_type_id
            )
        return result
