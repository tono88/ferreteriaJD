# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .common import is_transfer_flow


class StockPicking(models.Model):
    _inherit = "stock.picking"

    ferreteria_transfer_request_id = fields.Many2one(
        "ferreteria.transfer.request",
        string="Solicitud entre sucursales",
        copy=False,
        index=True,
        ondelete="restrict",
    )
    ferreteria_transfer_stage = fields.Selection(
        [
            ("dispatch", "Despacho a tránsito"),
            ("receipt", "Recepción desde tránsito"),
        ],
        string="Etapa de solicitud",
        copy=False,
        index=True,
    )

    def _ensure_transfer_flow_context(self, operation):
        protected = self.filtered("ferreteria_transfer_request_id")
        if protected and not is_transfer_flow(self.env):
            names = ", ".join(protected.mapped("name"))
            raise UserError(
                _(
                    "La operación '%(operation)s' no puede ejecutarse directamente sobre "
                    "los pickings %(pickings)s. Utilice los botones de la solicitud entre "
                    "sucursales para mantener sincronizadas las cantidades y la trazabilidad.",
                    operation=operation,
                    pickings=names,
                )
            )


    @api.model_create_multi
    def create(self, vals_list):
        protected = {
            "ferreteria_transfer_request_id",
            "ferreteria_transfer_stage",
        }
        if not is_transfer_flow(self.env) and any(
            set(vals).intersection(protected) for vals in vals_list
        ):
            raise UserError(
                _("Los pickings de solicitudes solo pueden ser creados por el flujo interno.")
            )
        return super().create(vals_list)

    def write(self, vals):
        protected = self.filtered("ferreteria_transfer_request_id")
        structural_fields = {
            "ferreteria_transfer_request_id",
            "ferreteria_transfer_stage",
            "picking_type_id",
            "location_id",
            "location_dest_id",
            "company_id",
        }
        if (
            protected
            and set(vals).intersection(structural_fields)
            and not is_transfer_flow(self.env)
        ):
            raise UserError(
                _("La estructura del picking está protegida por la solicitud entre sucursales.")
            )
        return super().write(vals)

    def unlink(self):
        self._ensure_transfer_flow_context(_("Eliminar"))
        return super().unlink()

    def button_validate(self):
        self._ensure_transfer_flow_context(_("Validar"))
        return super().button_validate()

    def action_cancel(self):
        self._ensure_transfer_flow_context(_("Cancelar"))
        return super().action_cancel()

    def do_unreserve(self):
        self._ensure_transfer_flow_context(_("Liberar reserva"))
        return super().do_unreserve()
