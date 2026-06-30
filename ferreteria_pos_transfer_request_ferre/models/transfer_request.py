# -*- coding: utf-8 -*-

from odoo import _, Command, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero

from .common import is_transfer_flow, transfer_flow_context


REQUEST_STATES = [
    ("draft", "Borrador"),
    ("submitted", "Solicitada"),
    ("review", "En revisión"),
    ("approved", "Aprobada"),
    ("partial", "Aprobada parcialmente"),
    ("preparing", "En preparación"),
    ("rejected", "Rechazada"),
    ("dispatched", "Despachada"),
    ("received", "Recibida"),
    ("incident", "Con incidencia"),
    ("closed", "Cerrada"),
    ("cancelled", "Cancelada"),
]


class FerreteriaTransferRequest(models.Model):
    _name = "ferreteria.transfer.request"
    _description = "Solicitud de productos entre sucursales"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "request_date desc, id desc"
    _check_company_auto = True
    _sql_constraints = [
        (
            "different_warehouses",
            "CHECK(requesting_warehouse_id != supplying_warehouse_id)",
            "La sucursal solicitante y la suministradora deben ser distintas.",
        ),
    ]

    def _get_requesting_warehouse_domain(self):
        """Return the selectable destination warehouses for the current user.

        This field-level domain is evaluated by the server when the form metadata
        is loaded.  It avoids depending on the value of a non-stored computed
        many2many inside the web-client domain of a new unsaved record.
        """
        domain = [("company_id", "=", self.env.company.id)]
        if self.env.user.has_group(
            "ferreteria_pos_transfer_request_ferre.group_transfer_request_admin"
        ):
            return domain
        return domain + [
            ("id", "in", self.env.user.ferreteria_request_warehouse_ids.ids)
        ]

    def _get_requesting_pos_domain(self):
        domain = [("company_id", "=", self.env.company.id)]
        if self.env.user.has_group(
            "ferreteria_pos_transfer_request_ferre.group_transfer_request_admin"
        ):
            return domain
        return domain + [
            ("id", "in", self.env.user.ferreteria_request_pos_ids.ids)
        ]

    def _default_requesting_warehouse(self):
        """Default the destination only when it can be derived unambiguously."""
        default_pos_id = self.env.context.get("default_requesting_pos_id")
        if default_pos_id:
            pos = self.env["pos.config"].browse(default_pos_id).exists()
            if pos and pos.company_id == self.env.company:
                return pos._ferreteria_transfer_warehouse()

        Warehouse = self.env["stock.warehouse"]
        if self.env.user.has_group(
            "ferreteria_pos_transfer_request_ferre.group_transfer_request_admin"
        ):
            warehouses = Warehouse.search(
                [("company_id", "=", self.env.company.id)], limit=2
            )
        else:
            warehouses = self.env.user.ferreteria_request_warehouse_ids.filtered(
                lambda warehouse: warehouse.company_id == self.env.company
            )
        return warehouses if len(warehouses) == 1 else Warehouse

    name = fields.Char(
        string="Referencia",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("Nuevo"),
        tracking=True,
        index=True,
    )
    state = fields.Selection(
        REQUEST_STATES,
        string="Estado",
        required=True,
        default="draft",
        copy=False,
        tracking=True,
        index=True,
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    requester_id = fields.Many2one(
        "res.users",
        string="Solicitado por",
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
        index=True,
        check_company=True,
    )
    request_date = fields.Datetime(
        string="Fecha de solicitud",
        required=True,
        default=fields.Datetime.now,
        tracking=True,
        index=True,
    )
    submitted_at = fields.Datetime(string="Fecha de envío", copy=False, readonly=True)
    reviewing_user_id = fields.Many2one(
        "res.users", string="Revisado por", copy=False, readonly=True, tracking=True
    )
    review_date = fields.Datetime(string="Fecha de revisión", copy=False, readonly=True)
    approved_by_id = fields.Many2one(
        "res.users", string="Aprobado por", copy=False, readonly=True, tracking=True
    )
    approval_date = fields.Datetime(string="Fecha de aprobación", copy=False, readonly=True)
    dispatched_by_id = fields.Many2one(
        "res.users", string="Despachado por", copy=False, readonly=True, tracking=True
    )
    dispatch_date = fields.Datetime(string="Fecha de despacho", copy=False, readonly=True)
    received_by_id = fields.Many2one(
        "res.users", string="Recibido por", copy=False, readonly=True, tracking=True
    )
    receipt_date = fields.Datetime(string="Fecha de recepción", copy=False, readonly=True)
    closed_by_id = fields.Many2one(
        "res.users", string="Cerrado por", copy=False, readonly=True, tracking=True
    )
    closed_date = fields.Datetime(string="Fecha de cierre", copy=False, readonly=True)

    allowed_requesting_warehouse_ids = fields.Many2many(
        "stock.warehouse",
        compute="_compute_allowed_requesting_warehouses",
        string="Almacenes solicitantes permitidos",
    )
    requesting_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Sucursal solicitante",
        required=True,
        default=_default_requesting_warehouse,
        domain=lambda self: self._get_requesting_warehouse_domain(),
        tracking=True,
        index=True,
        check_company=True,
    )
    supplying_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Sucursal suministradora",
        required=True,
        tracking=True,
        index=True,
        check_company=True,
    )
    requesting_pos_id = fields.Many2one(
        "pos.config",
        string="Punto de venta solicitante",
        tracking=True,
        index=True,
        check_company=True,
        domain=lambda self: self._get_requesting_pos_domain(),
        help=(
            "En el POS se completa automáticamente. En backend debe seleccionarse "
            "cuando el permiso de solicitar fue asignado a un POS específico."
        ),
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Cliente interesado",
        tracking=True,
        check_company=True,
        help="Dato informativo; no crea venta, factura, pago ni cuenta por cobrar.",
    )
    transit_location_id = fields.Many2one(
        "stock.location",
        string="Ubicación de tránsito",
        required=True,
        readonly=True,
        default=lambda self: self.env.ref(
            "ferreteria_pos_transfer_request_ferre.location_interbranch_transit",
            raise_if_not_found=False,
        ),
        check_company=True,
    )

    request_note = fields.Text(string="Observación de solicitud", tracking=True)
    approval_note = fields.Text(copy=False, string="Observación de aprobación", tracking=True)
    rejection_reason = fields.Text(copy=False, string="Motivo de rechazo", tracking=True)
    dispatch_note = fields.Text(copy=False, string="Observación de despacho", tracking=True)
    receipt_note = fields.Text(copy=False, string="Observación de recepción", tracking=True)

    line_ids = fields.One2many(
        "ferreteria.transfer.request.line",
        "request_id",
        string="Productos solicitados",
        copy=True,
    )
    incident_ids = fields.One2many(
        "ferreteria.transfer.incident",
        "request_id",
        string="Incidencias",
        copy=False,
    )
    incident_count = fields.Integer(compute="_compute_counts")
    line_count = fields.Integer(compute="_compute_counts")

    dispatch_picking_id = fields.Many2one(
        "stock.picking",
        string="Picking de despacho",
        copy=False,
        readonly=True,
        tracking=True,
        check_company=True,
    )
    receipt_picking_id = fields.Many2one(
        "stock.picking",
        string="Picking de recepción",
        copy=False,
        readonly=True,
        tracking=True,
        check_company=True,
    )

    requested_qty_total = fields.Float(
        string="Total solicitado",
        compute="_compute_qty_totals",
        store=True,
        digits="Product Unit of Measure",
    )
    approved_qty_total = fields.Float(
        string="Total aprobado",
        compute="_compute_qty_totals",
        store=True,
        digits="Product Unit of Measure",
    )
    dispatched_qty_total = fields.Float(
        string="Total despachado",
        compute="_compute_qty_totals",
        store=True,
        digits="Product Unit of Measure",
    )
    received_qty_total = fields.Float(
        string="Total recibido",
        compute="_compute_qty_totals",
        store=True,
        digits="Product Unit of Measure",
    )

    _business_header_fields = {
        "requesting_warehouse_id",
        "supplying_warehouse_id",
        "requesting_pos_id",
        "partner_id",
        "request_date",
        "request_note",
        "company_id",
    }
    _system_fields = {
        "name",
        "state",
        "requester_id",
        "submitted_at",
        "reviewing_user_id",
        "review_date",
        "approved_by_id",
        "approval_date",
        "dispatched_by_id",
        "dispatch_date",
        "received_by_id",
        "receipt_date",
        "closed_by_id",
        "closed_date",
        "transit_location_id",
        "dispatch_picking_id",
        "receipt_picking_id",
    }

    @api.depends_context("uid", "company")
    def _compute_allowed_requesting_warehouses(self):
        Warehouse = self.env["stock.warehouse"]
        if self.env.user.has_group(
            "ferreteria_pos_transfer_request_ferre.group_transfer_request_admin"
        ):
            allowed = Warehouse.search([("company_id", "=", self.env.company.id)])
        else:
            allowed = self.env.user.ferreteria_request_warehouse_ids.filtered(
                lambda warehouse: warehouse.company_id == self.env.company
            )
        for request in self:
            request.allowed_requesting_warehouse_ids = allowed

    @api.depends("line_ids", "incident_ids")
    def _compute_counts(self):
        for request in self:
            request.line_count = len(request.line_ids)
            request.incident_count = len(request.incident_ids)

    @api.depends(
        "line_ids.requested_qty",
        "line_ids.approved_qty",
        "line_ids.dispatched_qty",
        "line_ids.received_qty",
    )
    def _compute_qty_totals(self):
        for request in self:
            request.requested_qty_total = sum(request.line_ids.mapped("requested_qty"))
            request.approved_qty_total = sum(request.line_ids.mapped("approved_qty"))
            request.dispatched_qty_total = sum(request.line_ids.mapped("dispatched_qty"))
            request.received_qty_total = sum(request.line_ids.mapped("received_qty"))

    @api.model_create_multi
    def create(self, vals_list):
        records_vals = []
        internal_flow = is_transfer_flow(self.env)
        for values in vals_list:
            vals = dict(values)
            if not internal_flow:
                # Los clientes RPC pueden reenviar valores por defecto de campos de solo
                # lectura. Se descartan y se sustituyen por valores controlados por el
                # servidor, en lugar de confiar en ellos o romper la creación normal.
                for field_name in self._system_fields:
                    vals.pop(field_name, None)
                vals["requester_id"] = self.env.user.id
                vals["company_id"] = self.env.company.id
                vals["state"] = "draft"
            if vals.get("name", _("Nuevo")) == _("Nuevo") or not internal_flow:
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "ferreteria.transfer.request"
                ) or _("Nuevo")
            vals.setdefault("requester_id", self.env.user.id)
            vals.setdefault("company_id", self.env.company.id)

            # The POS is the authoritative source of the destination branch when
            # it is supplied.  This also makes RPC/POS creation robust even if the
            # client sends only the POS configuration.
            requesting_pos_id = vals.get("requesting_pos_id")
            if requesting_pos_id and not vals.get("requesting_warehouse_id"):
                pos = self.env["pos.config"].browse(requesting_pos_id).exists()
                if pos:
                    pos_warehouse = pos._ferreteria_transfer_warehouse()
                    if pos_warehouse:
                        vals["requesting_warehouse_id"] = pos_warehouse.id

            # In backend, avoid forcing a choice when the user has exactly one
            # authorized destination warehouse.
            if not vals.get("requesting_warehouse_id"):
                default_warehouse = self._default_requesting_warehouse()
                if default_warehouse:
                    vals["requesting_warehouse_id"] = default_warehouse.id

            records_vals.append(vals)
        requests = super().create(records_vals)
        if not internal_flow:
            requests._check_create_authorization()
        return requests

    def write(self, vals):
        if not is_transfer_flow(self.env):
            fields_to_change = set(vals)
            protected = fields_to_change.intersection(self._system_fields)
            if protected:
                raise AccessError(
                    _(
                        "Los campos del flujo solo pueden modificarse mediante sus botones: %s",
                        ", ".join(sorted(protected)),
                    )
                )
            for request in self:
                if fields_to_change.intersection(self._business_header_fields):
                    if request.state != "draft":
                        raise UserError(_("Los datos principales solo pueden modificarse en borrador."))
                    request._ensure_requester_access()
                if "approval_note" in fields_to_change:
                    if request.state not in ("submitted", "review"):
                        raise UserError(_("La observación de aprobación solo puede editarse durante la revisión."))
                    request._ensure_approver_access()
                if "rejection_reason" in fields_to_change:
                    if request.state not in ("submitted", "review", "approved", "partial", "preparing"):
                        raise UserError(_("El motivo de rechazo no puede editarse en el estado actual."))
                    request._ensure_approver_access()
                if "dispatch_note" in fields_to_change:
                    if request.state not in ("approved", "partial", "preparing"):
                        raise UserError(_("La observación de despacho no puede editarse en el estado actual."))
                    request._ensure_dispatcher_access()
                if "receipt_note" in fields_to_change:
                    if request.state != "dispatched":
                        raise UserError(_("La observación de recepción solo puede editarse después del despacho."))
                    request._ensure_receiver_access()
                if "active" in fields_to_change and not request._is_admin():
                    raise AccessError(_("Solo el administrador puede archivar solicitudes."))
        return super().write(vals)

    def unlink(self):
        for request in self:
            if request.state not in ("draft", "cancelled"):
                raise UserError(_("Solo se pueden eliminar solicitudes en borrador o canceladas."))
            request._ensure_requester_access()
        return super().unlink()

    @api.onchange("requesting_pos_id")
    def _onchange_requesting_pos_id(self):
        for request in self:
            if not request.requesting_pos_id:
                continue
            request.requesting_warehouse_id = (
                request.requesting_pos_id._ferreteria_transfer_warehouse()
            )
            if request.supplying_warehouse_id == request.requesting_warehouse_id:
                request.supplying_warehouse_id = False

    @api.onchange("requesting_warehouse_id")
    def _onchange_requesting_warehouse_id(self):
        for request in self:
            if (
                request.requesting_pos_id
                and request.requesting_pos_id._ferreteria_transfer_warehouse()
                != request.requesting_warehouse_id
            ):
                request.requesting_pos_id = False
            if request.supplying_warehouse_id == request.requesting_warehouse_id:
                request.supplying_warehouse_id = False

    @api.constrains(
        "requesting_warehouse_id",
        "supplying_warehouse_id",
        "requesting_pos_id",
        "company_id",
    )
    def _check_branch_configuration(self):
        for request in self:
            if request.requesting_warehouse_id == request.supplying_warehouse_id:
                raise ValidationError(
                    _("La sucursal solicitante y la suministradora deben ser distintas.")
                )
            warehouses = request.requesting_warehouse_id | request.supplying_warehouse_id
            if any(warehouse.company_id != request.company_id for warehouse in warehouses):
                raise ValidationError(_("Los almacenes deben pertenecer a la compañía de la solicitud."))
            if request.requesting_pos_id:
                pos_warehouse = (
                    request.requesting_pos_id._ferreteria_transfer_warehouse()
                )
                if pos_warehouse != request.requesting_warehouse_id:
                    raise ValidationError(
                        _("El punto de venta solicitante no pertenece al almacén seleccionado.")
                    )

    @api.constrains("line_ids")
    def _check_lines_present_and_unique(self):
        for request in self:
            seen = set()
            for line in request.line_ids:
                key = (line.product_id.id, line.product_uom_id.id)
                if key in seen:
                    raise ValidationError(
                        _(
                            "El producto %(product)s está repetido con la misma unidad de medida.",
                            product=line.product_id.display_name,
                        )
                    )
                seen.add(key)

    def _lock_for_update(self):
        if not self.ids:
            return
        self.env.cr.execute(
            f"SELECT id FROM {self._table} WHERE id IN %s FOR UPDATE",
            [tuple(self.ids)],
        )
        self.invalidate_recordset()

    def _is_admin(self):
        return self.env.user.has_group(
            "ferreteria_pos_transfer_request_ferre.group_transfer_request_admin"
        )

    def _ensure_requester_access(self):
        self.ensure_one()
        if self._is_admin():
            return
        if self.requester_id != self.env.user:
            raise AccessError(_("Solo el creador puede modificar o enviar esta solicitud."))
        if not self.env.user._ferreteria_has_transfer_permission(
            "request",
            warehouse=self.requesting_warehouse_id,
            pos_config=self.requesting_pos_id,
        ):
            raise AccessError(
                _(
                    "No está autorizado para solicitar productos desde %(branch)s%(pos)s. "
                    "Configure el permiso Solicitar en Solicitudes entre sucursales > Permisos por sucursal.",
                    branch=self.requesting_warehouse_id.display_name,
                    pos=(" / " + self.requesting_pos_id.display_name) if self.requesting_pos_id else "",
                )
            )

    def _ensure_approver_access(self):
        self.ensure_one()
        if self._is_admin():
            return
        if not self.env.user._ferreteria_has_transfer_permission(
            "approve", warehouse=self.supplying_warehouse_id
        ):
            raise AccessError(
                _(
                    "No está autorizado para aprobar o rechazar solicitudes de %(branch)s.",
                    branch=self.supplying_warehouse_id.display_name,
                )
            )

    def _ensure_dispatcher_access(self):
        self.ensure_one()
        if self._is_admin():
            return
        if not self.env.user._ferreteria_has_transfer_permission(
            "dispatch", warehouse=self.supplying_warehouse_id
        ):
            raise AccessError(
                _(
                    "No está autorizado para preparar o despachar desde %(branch)s.",
                    branch=self.supplying_warehouse_id.display_name,
                )
            )

    def _ensure_receiver_access(self):
        self.ensure_one()
        if self._is_admin():
            return
        if not self.env.user._ferreteria_has_transfer_permission(
            "receive", warehouse=self.requesting_warehouse_id
        ):
            raise AccessError(
                _(
                    "No está autorizado para recibir o cerrar solicitudes en %(branch)s.",
                    branch=self.requesting_warehouse_id.display_name,
                )
            )

    def _ensure_incident_access(self):
        self.ensure_one()
        if self._is_admin():
            return
        user = self.env.user
        can_report_from_source = (
            user._ferreteria_has_transfer_permission(
                "approve", warehouse=self.supplying_warehouse_id
            )
            or user._ferreteria_has_transfer_permission(
                "dispatch", warehouse=self.supplying_warehouse_id
            )
        )
        can_report_from_destination = user._ferreteria_has_transfer_permission(
            "receive", warehouse=self.requesting_warehouse_id
        )
        if not (can_report_from_source or can_report_from_destination):
            raise AccessError(_("No está autorizado para registrar incidencias en esta solicitud."))

    def _check_create_authorization(self):
        for request in self:
            request._ensure_requester_access()

    def _validate_request_lines(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("Debe agregar al menos un producto."))
        for line in self.line_ids:
            if float_compare(
                line.requested_qty,
                0.0,
                precision_rounding=line.product_uom_id.rounding,
            ) <= 0:
                raise UserError(
                    _("La cantidad solicitada de %(product)s debe ser mayor que cero.", product=line.product_id.display_name)
                )

    def action_submit(self):
        for request in self:
            request._lock_for_update()
            request._ensure_requester_access()
            if request.state != "draft":
                raise UserError(_("Solo las solicitudes en borrador pueden enviarse."))
            request._validate_request_lines()
            request.with_context(**transfer_flow_context()).write(
                {
                    "state": "submitted",
                    "submitted_at": fields.Datetime.now(),
                }
            )
            request.message_post(body=_("Solicitud enviada para revisión."))
        return True

    def action_start_review(self):
        for request in self:
            request._lock_for_update()
            request._ensure_approver_access()
            if request.state != "submitted":
                raise UserError(_("Solo una solicitud enviada puede ponerse en revisión."))
            request.with_context(**transfer_flow_context()).write(
                {
                    "state": "review",
                    "reviewing_user_id": self.env.user.id,
                    "review_date": fields.Datetime.now(),
                }
            )
        return True

    def action_approve_all(self):
        return self._action_approve(approve_all=True)

    def action_approve_partial(self):
        return self._action_approve(approve_all=False)

    def _action_approve(self, approve_all=False):
        for request in self:
            request._lock_for_update()
            request._ensure_approver_access()
            if request.state not in ("submitted", "review"):
                raise UserError(_("La solicitud ya fue procesada o no está pendiente de aprobación."))
            if approve_all:
                for line in request.line_ids:
                    line.with_context(**transfer_flow_context()).write(
                        {"approved_qty": line.requested_qty}
                    )
            request._validate_request_lines()
            request._validate_approval_quantities()
            request._create_and_reserve_pickings()
            fully_approved = all(
                float_compare(
                    line.approved_qty,
                    line.requested_qty,
                    precision_rounding=line.product_uom_id.rounding,
                ) == 0
                for line in request.line_ids
            )
            request.with_context(**transfer_flow_context()).write(
                {
                    "state": "approved" if fully_approved else "partial",
                    "approved_by_id": self.env.user.id,
                    "approval_date": fields.Datetime.now(),
                    "reviewing_user_id": request.reviewing_user_id.id or self.env.user.id,
                    "review_date": request.review_date or fields.Datetime.now(),
                }
            )
            request.message_post(
                body=_(
                    "Solicitud aprobada. Se reservaron %(qty)s unidades en el picking %(picking)s.",
                    qty=request.approved_qty_total,
                    picking=request.dispatch_picking_id.display_name,
                )
            )
        return True

    def _validate_approval_quantities(self):
        self.ensure_one()
        approved_lines = self.line_ids.filtered(
            lambda line: float_compare(
                line.approved_qty,
                0.0,
                precision_rounding=line.product_uom_id.rounding,
            ) > 0
        )
        if not approved_lines:
            raise UserError(_("Debe aprobar una cantidad mayor que cero en al menos una línea."))
        for line in self.line_ids:
            if float_compare(
                line.approved_qty,
                0.0,
                precision_rounding=line.product_uom_id.rounding,
            ) < 0:
                raise UserError(_("La cantidad aprobada no puede ser negativa."))
            if float_compare(
                line.approved_qty,
                line.requested_qty,
                precision_rounding=line.product_uom_id.rounding,
            ) > 0:
                raise UserError(
                    _(
                        "La cantidad aprobada de %(product)s no puede superar la solicitada.",
                        product=line.product_id.display_name,
                    )
                )

    def _prepare_picking_values(self, stage):
        self.ensure_one()
        if stage == "dispatch":
            warehouse = self.supplying_warehouse_id
            picking_type = warehouse.int_type_id
            source = warehouse.lot_stock_id
            destination = self.transit_location_id
        else:
            warehouse = self.requesting_warehouse_id
            picking_type = warehouse.int_type_id
            source = self.transit_location_id
            destination = warehouse.lot_stock_id
        if not picking_type:
            raise UserError(
                _("El almacén %(warehouse)s no tiene un tipo de operación interna.", warehouse=warehouse.display_name)
            )
        if not source or not destination:
            raise UserError(_("No se pudieron determinar las ubicaciones de la transferencia."))
        return {
            "picking_type_id": picking_type.id,
            "location_id": source.id,
            "location_dest_id": destination.id,
            "company_id": self.company_id.id,
            "origin": self.name,
            "partner_id": self.partner_id.id or False,
            "ferreteria_transfer_request_id": self.id,
            "ferreteria_transfer_stage": stage,
        }

    def _prepare_move_values(self, line, picking, source, destination):
        self.ensure_one()
        return {
            "name": _("%(request)s - %(product)s", request=self.name, product=line.product_id.display_name),
            "product_id": line.product_id.id,
            "product_uom": line.product_uom_id.id,
            "product_uom_qty": line.approved_qty,
            "location_id": source.id,
            "location_dest_id": destination.id,
            "picking_id": picking.id,
            "company_id": self.company_id.id,
            "origin": self.name,
            "procure_method": "make_to_stock",
        }

    def _create_and_reserve_pickings(self):
        self.ensure_one()
        if self.dispatch_picking_id or self.receipt_picking_id:
            raise UserError(_("La solicitud ya tiene movimientos de inventario vinculados."))

        Picking = self.env["stock.picking"]
        Move = self.env["stock.move"]
        protected_picking = Picking.with_context(**transfer_flow_context())
        dispatch_picking = protected_picking.create(
            self._prepare_picking_values("dispatch")
        )
        receipt_picking = protected_picking.create(
            self._prepare_picking_values("receipt")
        )

        dispatch_moves = self.env["stock.move"]
        receipt_moves = self.env["stock.move"]
        for line in self.line_ids.filtered(lambda current: current.approved_qty > 0):
            dispatch_move = Move.create(
                self._prepare_move_values(
                    line,
                    dispatch_picking,
                    self.supplying_warehouse_id.lot_stock_id,
                    self.transit_location_id,
                )
            )
            receipt_values = self._prepare_move_values(
                line,
                receipt_picking,
                self.transit_location_id,
                self.requesting_warehouse_id.lot_stock_id,
            )
            receipt_values.update(
                {
                    "move_orig_ids": [Command.link(dispatch_move.id)],
                    # El segundo movimiento debe esperar al despacho concreto y no
                    # reservar saldo residual de otras solicitudes en tránsito.
                    "procure_method": "make_to_order",
                }
            )
            receipt_move = Move.create(receipt_values)
            line.with_context(**transfer_flow_context()).write(
                {
                    "dispatch_move_id": dispatch_move.id,
                    "receipt_move_id": receipt_move.id,
                }
            )
            dispatch_moves |= dispatch_move
            receipt_moves |= receipt_move

        dispatch_moves._action_confirm(merge=False)
        receipt_moves._action_confirm(merge=False)
        dispatch_moves._action_assign()

        insufficient = []
        for line in self.line_ids.filtered("dispatch_move_id"):
            move = line.dispatch_move_id
            reserved_qty = move.quantity
            if float_compare(
                reserved_qty,
                line.approved_qty,
                precision_rounding=line.product_uom_id.rounding,
            ) < 0:
                insufficient.append(
                    _(
                        "%(product)s: aprobado %(approved)s, reservado %(reserved)s",
                        product=line.product_id.display_name,
                        approved=line.approved_qty,
                        reserved=reserved_qty,
                    )
                )
            line.with_context(**transfer_flow_context()).write({"reserved_qty": reserved_qty})

        if insufficient:
            raise UserError(
                _(
                    "No fue posible reservar completamente las cantidades aprobadas. "
                    "La aprobación se revirtió:\n%s",
                    "\n".join(insufficient),
                )
            )

        self.with_context(**transfer_flow_context()).write(
            {
                "dispatch_picking_id": dispatch_picking.id,
                "receipt_picking_id": receipt_picking.id,
            }
        )

    def action_start_preparation(self):
        for request in self:
            request._lock_for_update()
            request._ensure_dispatcher_access()
            if request.state not in ("approved", "partial"):
                raise UserError(_("Solo una solicitud aprobada puede ponerse en preparación."))
            request.with_context(**transfer_flow_context()).write({"state": "preparing"})
        return True

    def action_reject(self):
        for request in self:
            request._lock_for_update()
            request._ensure_approver_access()
            if request.state not in ("submitted", "review", "approved", "partial", "preparing"):
                raise UserError(_("La solicitud ya no puede rechazarse en su estado actual."))
            if not request.rejection_reason:
                raise UserError(_("Debe indicar el motivo del rechazo."))
            pickings = request.dispatch_picking_id | request.receipt_picking_id
            done_pickings = pickings.filtered(lambda picking: picking.state == "done")
            if done_pickings:
                raise UserError(_("No puede rechazarse una solicitud que ya fue despachada."))
            cancellable = pickings.filtered(lambda picking: picking.state != "cancel")
            if cancellable:
                cancellable.with_context(**transfer_flow_context()).action_cancel()
            request.line_ids.with_context(**transfer_flow_context()).write({"reserved_qty": 0.0})
            request.with_context(**transfer_flow_context()).write(
                {
                    "state": "rejected",
                    "reviewing_user_id": request.reviewing_user_id.id or self.env.user.id,
                    "review_date": request.review_date or fields.Datetime.now(),
                }
            )
            request.message_post(body=_("Solicitud rechazada: %s", request.rejection_reason))
        return True

    def action_cancel(self):
        for request in self:
            request._lock_for_update()
            request._ensure_requester_access()
            if request.state != "draft":
                raise UserError(_("Solo una solicitud en borrador puede cancelarse por el solicitante."))
            request.with_context(**transfer_flow_context()).write({"state": "cancelled"})
        return True

    def _validate_picking_result(self, result, operation):
        if isinstance(result, dict):
            raise UserError(
                _(
                    "Odoo solicitó un asistente adicional durante '%(operation)s'. "
                    "Revise lotes, series y cantidades en el picking y vuelva a ejecutar la acción.",
                    operation=operation,
                )
            )

    def _validate_picking_integrity(self, stage):
        self.ensure_one()
        if stage == "dispatch":
            picking = self.dispatch_picking_id
            expected_source = self.supplying_warehouse_id.lot_stock_id
            expected_destination = self.transit_location_id
            expected_picking_type = self.supplying_warehouse_id.int_type_id
            move_field = "dispatch_move_id"
            expected_stage = "dispatch"
        else:
            picking = self.receipt_picking_id
            expected_source = self.transit_location_id
            expected_destination = self.requesting_warehouse_id.lot_stock_id
            expected_picking_type = self.requesting_warehouse_id.int_type_id
            move_field = "receipt_move_id"
            expected_stage = "receipt"
        if not picking:
            raise UserError(_("No se encontró el picking de la etapa %s.", stage))
        if (
            picking.ferreteria_transfer_request_id != self
            or picking.ferreteria_transfer_stage != expected_stage
            or picking.company_id != self.company_id
            or picking.picking_type_id != expected_picking_type
            or picking.location_id != expected_source
            or picking.location_dest_id != expected_destination
        ):
            raise UserError(_("La configuración del picking vinculado fue modificada y ya no coincide con la solicitud."))

        expected_moves = self.env["stock.move"]
        for line in self.line_ids.filtered(lambda current: current.approved_qty > 0):
            move = line[move_field]
            if not move:
                raise UserError(_("Falta el movimiento de %(product)s.", product=line.product_id.display_name))
            expected_moves |= move
            invalid_move_lines = move.move_line_ids.filtered(
                lambda move_line: (
                    move_line.move_id != move
                    or move_line.product_id != line.product_id
                    or move_line.location_id != expected_source
                    or move_line.location_dest_id != expected_destination
                    or move_line.company_id != self.company_id
                )
            )
            if (
                move.picking_id != picking
                or move.product_id != line.product_id
                or move.product_uom != line.product_uom_id
                or move.location_id != expected_source
                or move.location_dest_id != expected_destination
                or move.company_id != self.company_id
                or invalid_move_lines
                or (
                    stage == "receipt"
                    and line.dispatch_move_id not in move.move_orig_ids
                )
                or float_compare(
                    move.product_uom_qty,
                    line.approved_qty,
                    precision_rounding=line.product_uom_id.rounding,
                ) != 0
            ):
                raise UserError(
                    _(
                        "El movimiento de %(product)s fue modificado y ya no coincide con la aprobación.",
                        product=line.product_id.display_name,
                    )
                )
        actual_moves = picking.move_ids.filtered(lambda move: move.state != "cancel")
        if set(actual_moves.ids) != set(expected_moves.ids):
            raise UserError(_("El picking contiene movimientos adicionales o faltantes."))
        return picking

    def action_dispatch(self):
        for request in self:
            request._lock_for_update()
            request._ensure_dispatcher_access()
            if request.state not in ("approved", "partial", "preparing"):
                raise UserError(_("La solicitud no está lista para despacho."))
            picking = request._validate_picking_integrity("dispatch")
            if picking.state in ("done", "cancel"):
                raise UserError(_("El picking de despacho no está disponible para validación."))
            picking.action_assign()
            insufficient = []
            for line in request.line_ids.filtered("dispatch_move_id"):
                move = line.dispatch_move_id
                if float_compare(
                    move.quantity,
                    line.approved_qty,
                    precision_rounding=line.product_uom_id.rounding,
                ) < 0:
                    insufficient.append(line.product_id.display_name)
            if insufficient:
                raise UserError(
                    _(
                        "La reserva dejó de estar completa para: %s. No se despachó ningún producto.",
                        ", ".join(insufficient),
                    )
                )
            picking.move_ids.write({"picked": True})
            result = picking.with_context(**transfer_flow_context()).button_validate()
            request._validate_picking_result(result, _("despacho"))
            if picking.state != "done":
                raise UserError(_("El picking de despacho no quedó validado."))

            values_by_line = {}
            for line in request.line_ids.filtered("dispatch_move_id"):
                qty = line.dispatch_move_id.quantity
                values_by_line[line.id] = {
                    "dispatched_qty": qty,
                    "received_qty": qty,
                }
            for line in request.line_ids:
                line.with_context(**transfer_flow_context()).write(
                    values_by_line.get(line.id, {"dispatched_qty": 0.0, "received_qty": 0.0})
                )

            request.receipt_picking_id.action_assign()
            request.with_context(**transfer_flow_context()).write(
                {
                    "state": "dispatched",
                    "dispatched_by_id": self.env.user.id,
                    "dispatch_date": fields.Datetime.now(),
                }
            )
            request.message_post(
                body=_("Despacho confirmado. Los productos se encuentran en tránsito.")
            )
        return True

    def _prepare_receipt_quantities(self):
        self.ensure_one()
        total = 0.0
        for line in self.line_ids.filtered("receipt_move_id"):
            line._validate_received_qty()
            move = line.receipt_move_id
            move.quantity = line.received_qty
            move.picked = not float_is_zero(
                line.received_qty, precision_rounding=line.product_uom_id.rounding
            )
            total += line.received_qty
        return total

    def _create_automatic_shortage_incidents(self):
        Incident = self.env["ferreteria.transfer.incident"]
        for line in self.line_ids:
            difference = line.dispatched_qty - line.received_qty
            if float_compare(
                difference, 0.0, precision_rounding=line.product_uom_id.rounding
            ) > 0:
                Incident.with_context(**transfer_flow_context()).create(
                    {
                        "request_id": self.id,
                        "line_id": line.id,
                        "incident_type": "shortage",
                        "incident_qty": difference,
                        "note": self.receipt_note or _("Diferencia detectada durante la recepción."),
                    }
                )

    def action_receive(self):
        for request in self:
            request._lock_for_update()
            request._ensure_receiver_access()
            if request.state != "dispatched":
                raise UserError(_("Solo una solicitud despachada puede recibirse."))
            picking = request._validate_picking_integrity("receipt")
            if picking.state in ("done", "cancel"):
                raise UserError(_("El picking de recepción no está disponible para validación."))
            picking.action_assign()
            total_received = request._prepare_receipt_quantities()
            if float_is_zero(total_received, precision_digits=6):
                picking.with_context(**transfer_flow_context()).action_cancel()
            else:
                result = picking.with_context(
                    picking_ids_not_to_backorder=picking.ids,
                    **transfer_flow_context(),
                ).button_validate()
                request._validate_picking_result(result, _("recepción"))
                if picking.state != "done":
                    raise UserError(_("El picking de recepción no quedó validado."))

            has_difference = any(
                float_compare(
                    line.received_qty,
                    line.dispatched_qty,
                    precision_rounding=line.product_uom_id.rounding,
                ) < 0
                for line in request.line_ids
            )
            if has_difference:
                request._create_automatic_shortage_incidents()
            request.with_context(**transfer_flow_context()).write(
                {
                    "state": "incident" if has_difference else "received",
                    "received_by_id": self.env.user.id,
                    "receipt_date": fields.Datetime.now(),
                }
            )
            request.message_post(
                body=_(
                    "Recepción confirmada. Cantidad recibida: %(received)s. Estado: %(state)s.",
                    received=request.received_qty_total,
                    state=request.state,
                )
            )
        return True

    def action_close(self):
        for request in self:
            request._lock_for_update()
            request._ensure_receiver_access()
            if request.state not in ("received", "incident"):
                raise UserError(_("Solo una solicitud recibida o con incidencia puede cerrarse."))
            if request.incident_ids.filtered(lambda incident: incident.state == "open"):
                raise UserError(_("Debe resolver todas las incidencias antes de cerrar la solicitud."))
            request.with_context(**transfer_flow_context()).write(
                {
                    "state": "closed",
                    "closed_by_id": self.env.user.id,
                    "closed_date": fields.Datetime.now(),
                }
            )
        return True

    def action_view_dispatch_picking(self):
        self.ensure_one()
        if not self.dispatch_picking_id:
            raise UserError(_("No existe picking de despacho."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Picking de despacho"),
            "res_model": "stock.picking",
            "view_mode": "form",
            "res_id": self.dispatch_picking_id.id,
        }

    def action_view_receipt_picking(self):
        self.ensure_one()
        if not self.receipt_picking_id:
            raise UserError(_("No existe picking de recepción."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Picking de recepción"),
            "res_model": "stock.picking",
            "view_mode": "form",
            "res_id": self.receipt_picking_id.id,
        }

    def action_view_incidents(self):
        self.ensure_one()
        action = self.env.ref(
            "ferreteria_pos_transfer_request_ferre.action_transfer_incident"
        ).read()[0]
        action["domain"] = [("request_id", "=", self.id)]
        action["context"] = {"default_request_id": self.id}
        return action

    def action_register_incident(self):
        self.ensure_one()
        self._ensure_incident_access()
        if self.state not in ("dispatched", "received", "incident"):
            raise UserError(_("Solo puede registrar incidencias después del despacho."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Registrar incidencia"),
            "res_model": "ferreteria.transfer.incident",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }


class FerreteriaTransferRequestLine(models.Model):
    _name = "ferreteria.transfer.request.line"
    _description = "Línea de solicitud entre sucursales"
    _order = "id"
    _check_company_auto = True
    _sql_constraints = [
        (
            "request_product_uom_unique",
            "unique(request_id, product_id, product_uom_id)",
            "El producto no puede repetirse con la misma unidad de medida.",
        ),
        (
            "quantity_chain_valid",
            "CHECK(requested_qty > 0 "
            "AND approved_qty >= 0 "
            "AND reserved_qty >= 0 "
            "AND dispatched_qty >= 0 "
            "AND received_qty >= 0 "
            "AND approved_qty <= requested_qty "
            "AND reserved_qty <= approved_qty "
            "AND dispatched_qty <= approved_qty "
            "AND received_qty <= dispatched_qty)",
            "Las cantidades de la línea no respetan la secuencia solicitud-aprobación-reserva-despacho-recepción.",
        ),
    ]

    request_id = fields.Many2one(
        "ferreteria.transfer.request",
        string="Solicitud",
        required=True,
        ondelete="cascade",
        index=True,
        check_company=True,
    )
    company_id = fields.Many2one(related="request_id.company_id", store=True, index=True)
    state = fields.Selection(related="request_id.state", store=True, index=True)
    product_id = fields.Many2one(
        "product.product",
        string="Producto",
        required=True,
        domain="[('is_storable', '=', True), ('active', '=', True)]",
        check_company=True,
    )
    product_uom_id = fields.Many2one(
        "uom.uom",
        string="Unidad de medida",
        required=True,
        domain="[('category_id', '=', product_uom_category_id)]",
    )
    product_uom_category_id = fields.Many2one(
        related="product_id.uom_id.category_id", readonly=True
    )
    requested_qty = fields.Float(
        string="Solicitada",
        required=True,
        default=1.0,
        digits="Product Unit of Measure",
    )
    approved_qty = fields.Float(
        string="Aprobada",
        default=0.0,
        copy=False,
        digits="Product Unit of Measure",
    )
    reserved_qty = fields.Float(
        string="Reservada",
        default=0.0,
        readonly=True,
        copy=False,
        digits="Product Unit of Measure",
    )
    dispatched_qty = fields.Float(
        string="Despachada",
        default=0.0,
        readonly=True,
        copy=False,
        digits="Product Unit of Measure",
    )
    received_qty = fields.Float(
        string="Recibida",
        default=0.0,
        copy=False,
        digits="Product Unit of Measure",
    )
    incident_qty = fields.Float(
        string="Con incidencia",
        compute="_compute_incident_qty",
        store=True,
        digits="Product Unit of Measure",
    )
    available_qty = fields.Float(
        string="Disponible informativo",
        compute="_compute_available_qty",
        digits="Product Unit of Measure",
        help="Existencia libre informativa del almacén suministrador. Se vuelve a validar al aprobar.",
    )
    note = fields.Char(string="Observación")
    dispatch_move_id = fields.Many2one(
        "stock.move", string="Movimiento de despacho", copy=False, readonly=True
    )
    receipt_move_id = fields.Many2one(
        "stock.move", string="Movimiento de recepción", copy=False, readonly=True
    )
    incident_ids = fields.One2many(
        "ferreteria.transfer.incident", "line_id", string="Incidencias", copy=False
    )

    @api.depends("incident_ids.incident_qty")
    def _compute_incident_qty(self):
        for line in self:
            line.incident_qty = sum(line.incident_ids.mapped("incident_qty"))

    @api.depends(
        "product_id",
        "product_uom_id",
        "request_id.supplying_warehouse_id",
    )
    def _compute_available_qty(self):
        for line in self:
            warehouse = line.request_id.supplying_warehouse_id
            if not line.product_id or not warehouse:
                line.available_qty = 0.0
                continue
            qty_product_uom = line.product_id.with_context(
                warehouse_id=warehouse.id
            ).free_qty
            line.available_qty = line.product_id.uom_id._compute_quantity(
                qty_product_uom,
                line.product_uom_id or line.product_id.uom_id,
                round=False,
            )

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for line in self:
            if line.product_id:
                line.product_uom_id = line.product_id.uom_id

    @api.model_create_multi
    def create(self, vals_list):
        internal_flow = is_transfer_flow(self.env)
        prepared_vals = []
        authorization_fields = []
        stage_fields = {
            "approved_qty",
            "reserved_qty",
            "dispatched_qty",
            "received_qty",
            "dispatch_move_id",
            "receipt_move_id",
        }
        for values in vals_list:
            vals = dict(values)
            if not internal_flow:
                for field_name in stage_fields:
                    vals.pop(field_name, None)
            if vals.get("product_id") and not vals.get("product_uom_id"):
                product = self.env["product.product"].browse(vals["product_id"])
                vals["product_uom_id"] = product.uom_id.id
            authorization_fields.append(set(vals))
            prepared_vals.append(vals)
        lines = super().create(prepared_vals)
        if not internal_flow:
            for line, fields_to_check in zip(lines, authorization_fields):
                line._ensure_edit_authorization(fields_to_check)
        return lines

    def write(self, vals):
        if not is_transfer_flow(self.env):
            for line in self:
                line._ensure_edit_authorization(set(vals.keys()))
        return super().write(vals)

    def unlink(self):
        if not is_transfer_flow(self.env):
            for line in self:
                if line.request_id.state != "draft":
                    raise UserError(_("Solo se pueden eliminar líneas en borrador."))
                line.request_id._ensure_requester_access()
        return super().unlink()

    def _ensure_edit_authorization(self, fields_to_change):
        self.ensure_one()
        request = self.request_id
        if request._is_admin():
            return
        request_fields = {"product_id", "product_uom_id", "requested_qty", "note", "request_id"}
        approval_fields = {"approved_qty"}
        receipt_fields = {"received_qty"}
        protected_fields = {
            "reserved_qty",
            "dispatched_qty",
            "dispatch_move_id",
            "receipt_move_id",
        }
        if fields_to_change & protected_fields:
            raise AccessError(_("Las cantidades técnicas solo pueden actualizarse por el flujo del sistema."))
        if fields_to_change <= request_fields:
            if request.state != "draft":
                raise UserError(_("Las líneas solicitadas solo pueden editarse en borrador."))
            request._ensure_requester_access()
            return
        if fields_to_change <= approval_fields:
            if request.state not in ("submitted", "review"):
                raise UserError(_("La cantidad aprobada solo puede editarse durante la revisión."))
            request._ensure_approver_access()
            return
        if fields_to_change <= receipt_fields:
            if request.state != "dispatched":
                raise UserError(_("La cantidad recibida solo puede editarse después del despacho."))
            request._ensure_receiver_access()
            return
        raise AccessError(_("No está autorizado para modificar esos campos de la línea."))

    @api.constrains("request_id", "product_id", "product_uom_id")
    def _check_duplicate_product_uom(self):
        for line in self:
            if not line.request_id or not line.product_id or not line.product_uom_id:
                continue
            duplicate = self.search_count(
                [
                    ("id", "!=", line.id),
                    ("request_id", "=", line.request_id.id),
                    ("product_id", "=", line.product_id.id),
                    ("product_uom_id", "=", line.product_uom_id.id),
                ],
                limit=1,
            )
            if duplicate:
                raise ValidationError(
                    _(
                        "El producto %(product)s está repetido con la misma unidad de medida.",
                        product=line.product_id.display_name,
                    )
                )

    @api.constrains(
        "requested_qty",
        "approved_qty",
        "reserved_qty",
        "dispatched_qty",
        "received_qty",
    )
    def _check_quantities(self):
        for line in self:
            rounding = line.product_uom_id.rounding or 0.01
            values = [
                line.requested_qty,
                line.approved_qty,
                line.reserved_qty,
                line.dispatched_qty,
                line.received_qty,
            ]
            if any(float_compare(value, 0.0, precision_rounding=rounding) < 0 for value in values):
                raise ValidationError(_("Las cantidades no pueden ser negativas."))
            if float_compare(line.approved_qty, line.requested_qty, precision_rounding=rounding) > 0:
                raise ValidationError(_("La cantidad aprobada no puede superar la solicitada."))
            if float_compare(line.reserved_qty, line.approved_qty, precision_rounding=rounding) > 0:
                raise ValidationError(_("La cantidad reservada no puede superar la aprobada."))
            if float_compare(line.dispatched_qty, line.approved_qty, precision_rounding=rounding) > 0:
                raise ValidationError(_("La cantidad despachada no puede superar la aprobada."))
            if float_compare(line.received_qty, line.dispatched_qty, precision_rounding=rounding) > 0:
                raise ValidationError(_("La cantidad recibida no puede superar la despachada."))

    @api.constrains("product_id", "product_uom_id")
    def _check_uom_category(self):
        for line in self:
            if (
                line.product_id
                and line.product_uom_id
                and line.product_id.uom_id.category_id != line.product_uom_id.category_id
            ):
                raise ValidationError(_("La unidad de medida no pertenece a la categoría del producto."))

    def _validate_received_qty(self):
        self.ensure_one()
        rounding = self.product_uom_id.rounding
        if float_compare(self.received_qty, 0.0, precision_rounding=rounding) < 0:
            raise UserError(_("La cantidad recibida no puede ser negativa."))
        if float_compare(
            self.received_qty,
            self.dispatched_qty,
            precision_rounding=rounding,
        ) > 0:
            raise UserError(
                _(
                    "La cantidad recibida de %(product)s no puede superar la despachada.",
                    product=self.product_id.display_name,
                )
            )
