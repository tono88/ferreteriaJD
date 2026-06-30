# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.float_utils import float_compare

from .common import is_transfer_flow, transfer_flow_context


class FerreteriaTransferIncident(models.Model):
    _name = "ferreteria.transfer.incident"
    _description = "Incidencia de transferencia entre sucursales"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "reported_at desc, id desc"
    _check_company_auto = True
    _sql_constraints = [
        (
            "incident_qty_positive",
            "CHECK(incident_qty > 0)",
            "La cantidad con incidencia debe ser mayor que cero.",
        ),
    ]

    name = fields.Char(
        string="Referencia",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("Nuevo"),
        tracking=True,
    )
    request_id = fields.Many2one(
        "ferreteria.transfer.request",
        string="Solicitud",
        required=True,
        ondelete="cascade",
        index=True,
        tracking=True,
        check_company=True,
    )
    company_id = fields.Many2one(related="request_id.company_id", store=True, index=True)
    line_id = fields.Many2one(
        "ferreteria.transfer.request.line",
        string="Producto afectado",
        required=True,
        domain="[('request_id', '=', request_id)]",
        tracking=True,
        check_company=True,
    )
    product_id = fields.Many2one(related="line_id.product_id", store=True, readonly=True)
    product_uom_id = fields.Many2one(
        related="line_id.product_uom_id", store=True, readonly=True
    )
    incident_type = fields.Selection(
        [
            ("loss", "Pérdida"),
            ("damage", "Daño"),
            ("shortage", "Faltante"),
            ("quantity_difference", "Diferencia de cantidad"),
            ("transport_error", "Error de transporte"),
            ("other", "Otro"),
        ],
        string="Tipo",
        required=True,
        default="shortage",
        tracking=True,
    )
    dispatched_qty = fields.Float(
        related="line_id.dispatched_qty",
        string="Cantidad despachada",
        readonly=True,
        digits="Product Unit of Measure",
    )
    received_qty = fields.Float(
        related="line_id.received_qty",
        string="Cantidad recibida",
        readonly=True,
        digits="Product Unit of Measure",
    )
    incident_qty = fields.Float(
        string="Cantidad con incidencia",
        required=True,
        digits="Product Unit of Measure",
        tracking=True,
    )
    reported_by_id = fields.Many2one(
        "res.users",
        string="Reportado por",
        required=True,
        default=lambda self: self.env.user,
        readonly=True,
        tracking=True,
    )
    reported_at = fields.Datetime(
        string="Fecha de reporte",
        required=True,
        default=fields.Datetime.now,
        readonly=True,
        tracking=True,
    )
    note = fields.Text(string="Observación", required=True, tracking=True)
    state = fields.Selection(
        [("open", "Abierta"), ("resolved", "Resuelta")],
        string="Estado",
        required=True,
        default="open",
        tracking=True,
        index=True,
    )
    resolved_by_id = fields.Many2one(
        "res.users", string="Resuelta por", readonly=True, copy=False
    )
    resolved_at = fields.Datetime(string="Fecha de resolución", readonly=True, copy=False)
    resolution_note = fields.Text(string="Resolución", tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        prepared = []
        internal_flow = is_transfer_flow(self.env)
        protected = {
            "state",
            "reported_by_id",
            "reported_at",
            "resolved_by_id",
            "resolved_at",
        }
        for values in vals_list:
            vals = dict(values)
            if not internal_flow:
                for field_name in protected:
                    vals.pop(field_name, None)
            vals["name"] = self.env["ir.sequence"].next_by_code(
                "ferreteria.transfer.incident"
            ) or _("Nuevo")
            vals["reported_by_id"] = self.env.user.id
            vals["reported_at"] = fields.Datetime.now()
            vals.setdefault("state", "open")
            prepared.append(vals)
        incidents = super().create(prepared)
        if not internal_flow:
            incidents._ensure_report_authorization()
        incidents._validate_request_stage()
        for request in incidents.request_id:
            if request.state in ("dispatched", "received"):
                request.with_context(**transfer_flow_context()).write({"state": "incident"})
            incident_names = ", ".join(
                incidents.filtered(lambda incident: incident.request_id == request).mapped("name")
            )
            request.message_post(body=_("Se registró la incidencia %s.", incident_names))
        return incidents

    def write(self, vals):
        if not is_transfer_flow(self.env):
            self._ensure_report_authorization()
            protected = {
                "name",
                "request_id",
                "line_id",
                "state",
                "reported_by_id",
                "reported_at",
                "resolved_by_id",
                "resolved_at",
            }
            if set(vals).intersection(protected):
                raise AccessError(_("Los campos de trazabilidad solo pueden modificarse mediante las acciones del flujo."))
            if self.filtered(lambda incident: incident.state == "resolved") and set(vals) - {"resolution_note"}:
                raise UserError(_("Una incidencia resuelta no puede modificarse."))
        return super().write(vals)

    def unlink(self):
        if not is_transfer_flow(self.env):
            if not self.env.user.has_group(
                "ferreteria_pos_transfer_request_ferre.group_transfer_request_admin"
            ):
                raise AccessError(_("Solo el administrador puede eliminar incidencias."))
        return super().unlink()

    def _ensure_report_authorization(self):
        for incident in self:
            incident.request_id._ensure_incident_access()

    def _validate_request_stage(self):
        for incident in self:
            if incident.request_id.state not in ("dispatched", "received", "incident"):
                raise ValidationError(_("Las incidencias solo pueden registrarse después del despacho."))
            if incident.line_id and incident.line_id.request_id != incident.request_id:
                raise ValidationError(_("La línea seleccionada no pertenece a la solicitud."))

    @api.constrains("incident_qty", "line_id")
    def _check_incident_qty(self):
        for incident in self:
            if not incident.line_id:
                continue
            rounding = incident.product_uom_id.rounding
            if float_compare(incident.incident_qty, 0.0, precision_rounding=rounding) <= 0:
                raise ValidationError(_("La cantidad con incidencia debe ser mayor que cero."))
            other_qty = sum(
                incident.line_id.incident_ids.filtered(lambda current: current != incident).mapped(
                    "incident_qty"
                )
            )
            if float_compare(
                other_qty + incident.incident_qty,
                incident.line_id.dispatched_qty,
                precision_rounding=rounding,
            ) > 0:
                raise ValidationError(
                    _("La suma de incidencias no puede superar la cantidad despachada.")
                )

    def action_resolve(self):
        for incident in self:
            incident._ensure_report_authorization()
            if incident.state != "open":
                raise UserError(_("La incidencia ya está resuelta."))
            if not incident.resolution_note:
                raise UserError(_("Debe registrar una nota de resolución."))
            incident.with_context(**transfer_flow_context()).write(
                {
                    "state": "resolved",
                    "resolved_by_id": self.env.user.id,
                    "resolved_at": fields.Datetime.now(),
                }
            )
        return {"type": "ir.actions.act_window_close"}
