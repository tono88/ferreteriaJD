from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    ferreteria_done_by_id = fields.Many2one(
        "res.users",
        string="Usuario que completó",
        readonly=True,
        copy=False,
        index=True,
        help="Se captura al completar el movimiento después de instalar este módulo.",
    )
    ferreteria_report_user_id = fields.Many2one(
        "res.users",
        string="Usuario",
        compute="_compute_ferreteria_report_context",
        help="Usuario capturado al completar. Para históricos: última escritura del picking o movimiento.",
    )
    ferreteria_supplier_id = fields.Many2one(
        "res.partner",
        string="Proveedor",
        compute="_compute_ferreteria_report_context",
    )

    @api.depends(
        "ferreteria_done_by_id",
        "write_uid",
        "picking_id.write_uid",
        "purchase_line_id.order_id.partner_id",
        "location_id.usage",
        "state",
    )
    def _compute_ferreteria_report_context(self):
        for move in self:
            move.ferreteria_report_user_id = (
                move.ferreteria_done_by_id
                or move.picking_id.write_uid
                or move.write_uid
            )
            move.ferreteria_supplier_id = False
            if (
                move.state == "done"
                and move.location_id.usage == "supplier"
                and move.purchase_line_id
            ):
                move.ferreteria_supplier_id = move.purchase_line_id.order_id.partner_id

    def _action_done(self, cancel_backorder=False):
        moves = super()._action_done(cancel_backorder=cancel_backorder)
        candidates = (self | moves).exists()
        candidates.invalidate_recordset(["state", "ferreteria_done_by_id"])
        completed = candidates.filtered(
            lambda move: move.state == "done" and not move.ferreteria_done_by_id
        )
        completed.write({
            "ferreteria_done_by_id": self.env.user.id,
        })
        return moves


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    ferreteria_report_user_id = fields.Many2one(
        related="move_id.ferreteria_report_user_id",
        string="Usuario",
        readonly=True,
    )
    ferreteria_supplier_id = fields.Many2one(
        related="move_id.ferreteria_supplier_id",
        string="Proveedor",
        readonly=True,
    )
