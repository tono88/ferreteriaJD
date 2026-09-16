# -*- coding: utf-8 -*-

import logging

from odoo import models


_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    def _ferreteria_impacted_stock_min_orderpoints(self):
        """Return replenishment rules impacted by these completed stock moves.

        A rule is impacted when it belongs to the same product/company and its
        replenishment location is the same as, or a parent of, an internal
        source/destination location touched by the move.
        """
        moves = self.filtered(
            lambda move: move.state == "done"
            and move.product_id
            and move.product_id.is_storable
            and (
                move.location_id.usage == "internal"
                or move.location_dest_id.usage == "internal"
            )
        )
        if not moves:
            return self.env["stock.warehouse.orderpoint"]

        orderpoints = self.env["stock.warehouse.orderpoint"].sudo().search(
            [
                ("active", "=", True),
                ("product_id", "in", moves.product_id.ids),
                ("company_id", "in", moves.company_id.ids),
            ]
        )
        if not orderpoints:
            return orderpoints

        locations_by_product_company = {}
        for move in moves:
            key = (move.product_id.id, move.company_id.id)
            locations = locations_by_product_company.setdefault(
                key, self.env["stock.location"]
            )
            if move.location_id.usage == "internal":
                locations |= move.location_id
            if move.location_dest_id.usage == "internal":
                locations |= move.location_dest_id
            locations_by_product_company[key] = locations

        impacted = self.env["stock.warehouse.orderpoint"]
        for orderpoint in orderpoints:
            key = (orderpoint.product_id.id, orderpoint.company_id.id)
            impacted_locations = locations_by_product_company.get(key)
            if not impacted_locations:
                continue
            if any(
                location._child_of(orderpoint.location_id)
                for location in impacted_locations
            ):
                impacted |= orderpoint

        return impacted

    def _ferreteria_check_stock_min_alerts_after_done(self):
        """Evaluate only the replenishment rules affected by completed moves."""
        orderpoints = self._ferreteria_impacted_stock_min_orderpoints()
        if not orderpoints:
            return

        # Ensure quantities are recomputed using the stock state produced by the
        # completed operation instead of any value cached earlier in the request.
        orderpoints.mapped("product_id").invalidate_recordset(
            ["qty_available", "virtual_available"]
        )
        orderpoints.invalidate_recordset(
            [
                "qty_on_hand",
                "qty_forecast",
                "qty_to_order_computed",
                "qty_to_order",
            ]
        )
        stats = orderpoints.with_context(
            ferreteria_stock_alert_automatic=True
        )._ferreteria_process_stock_min_alerts()
        _logger.info(
            "Revisión inmediata de alertas tras movimientos de inventario %s: %s",
            self.ids,
            stats,
        )

    def _action_done(self, cancel_backorder=False):
        done_moves = super()._action_done(cancel_backorder=cancel_backorder)

        if (
            done_moves
            and not self.env.context.get("ferreteria_skip_stock_min_alert")
        ):
            try:
                done_moves._ferreteria_check_stock_min_alerts_after_done()
            except Exception:
                # A failure in a notification must never roll back a POS sale,
                # delivery, receipt, transfer or inventory adjustment. The hourly
                # cron remains as a safety net and will retry the evaluation.
                _logger.exception(
                    "No fue posible evaluar inmediatamente las alertas de "
                    "reabastecimiento tras completar los movimientos %s. "
                    "El cron periódico realizará un nuevo intento.",
                    done_moves.ids,
                )

        return done_moves
