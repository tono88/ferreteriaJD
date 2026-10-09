# Copyright 2026 Ferretería JD. LGPL-3.
from odoo import _, models
from odoo.exceptions import UserError


class PosOrder(models.Model):
    _inherit = "pos.order"

    def _ferreteria_get_quotation(self):
        self.ensure_one()
        sales = self.lines.mapped("sale_order_origin_id").filtered("is_pos_created")
        if not sales:
            return self.env["sale.order"]
        if len(sales) != 1 or any(
            not line.sale_order_origin_id or line.sale_order_origin_id != sales
            for line in self.lines
        ):
            raise UserError(_(
                "No mezcle artículos de diferentes pedidos en el cobro de una cotización. "
                "Genere una venta POS independiente."
            ))
        return sales

    def _ferreteria_assert_single_checkout(self):
        """Impedir segundo cobro/factura concurrente de la misma cotización.

        El bloqueo de fila dura hasta confirmar la transacción de sincronización
        (incluido el movimiento de stock y la generación de factura FEL).
        """
        for order in self:
            quotation = order._ferreteria_get_quotation()
            if not quotation:
                continue
            self.env.cr.execute(
                "SELECT id FROM sale_order WHERE id = %s FOR UPDATE", [quotation.id]
            )
            if quotation.company_id != order.company_id or (
                quotation.warehouse_id != order.config_id.picking_type_id.warehouse_id
            ):
                raise UserError(_("El pedido y el POS tienen empresa o almacén diferente."))
            if quotation.ferreteria_pos_invoice_ids.filtered(
                lambda invoice: invoice.state != "cancel"
            ):
                raise UserError(_("Esta cotización ya tiene una factura POS."))
            if quotation.order_line.mapped("invoice_lines").filtered(
                lambda line: line.move_id.state != "cancel"
            ):
                raise UserError(_("Esta cotización ya fue facturada desde Ventas."))
            other_paid = self.search([
                ("id", "!=", order.id),
                ("lines.sale_order_origin_id", "=", quotation.id),
                ("state", "in", ("paid", "done", "invoiced")),
            ], limit=1)
            if other_paid:
                raise UserError(_(
                    "La cotización ya fue cobrada en %(pos)s. "
                    "Consulte la factura existente.",
                    pos=other_paid.display_name,
                ))
            if not order.to_invoice:
                raise UserError(_(
                    "La cotización debe facturarse desde este POS. "
                    "Active Factura en la pantalla de pago."
                ))
        return True

    def _process_saved_order(self, draft):
        # El núcleo captura algunas excepciones de action_pos_order_paid()
        # y todavía intenta crear movimientos: validar ANTES de su llamada.
        if not draft:
            self._ferreteria_assert_single_checkout()
        return super()._process_saved_order(draft)

    def action_pos_order_paid(self):
        self._ferreteria_assert_single_checkout()
        return super().action_pos_order_paid()

    def _prepare_invoice_vals(self):
        values = super()._prepare_invoice_vals()
        quotation = self._ferreteria_get_quotation()
        if quotation:
            # Un único comprobante FEL creado por el POS; Ventas NO crea otro.
            values["ferreteria_pos_sale_order_id"] = quotation.id
            values["invoice_origin"] = quotation.name
        return values
