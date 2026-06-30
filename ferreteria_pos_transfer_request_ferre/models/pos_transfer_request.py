# -*- coding: utf-8 -*-

from math import isfinite

from odoo import _, Command, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.float_utils import float_round


class FerreteriaTransferRequestPos(models.Model):
    _inherit = "ferreteria.transfer.request"

    @api.model
    def _pos_validate_request_context(self, pos_config_id):
        """Validate that the current RPC user may request for this POS branch."""
        pos_config = self.env["pos.config"].browse(int(pos_config_id or 0)).exists()
        if not pos_config:
            raise UserError(_("No se encontró la configuración del punto de venta."))
        if pos_config.company_id != self.env.company:
            raise AccessError(_("El punto de venta no pertenece a la compañía activa."))
        pos_warehouse = pos_config._ferreteria_transfer_warehouse()
        if not pos_warehouse:
            raise UserError(
                _("El tipo de operación del punto de venta no tiene un almacén asociado.")
            )

        if not self.env.user._ferreteria_has_transfer_permission(
            "request",
            warehouse=pos_warehouse,
            pos_config=pos_config,
        ):
            raise AccessError(
                _(
                    "Su usuario no tiene permiso para solicitar desde %(pos)s / %(warehouse)s. "
                    "Asigne el permiso Solicitar en Solicitudes entre sucursales > Permisos por sucursal.",
                    pos=pos_config.display_name,
                    warehouse=pos_warehouse.display_name,
                )
            )
        return pos_config

    @api.model
    def _pos_validate_supplying_warehouse(self, pos_config, warehouse_id):
        warehouse = self.env["stock.warehouse"].browse(int(warehouse_id or 0)).exists()
        if not warehouse:
            raise UserError(_("Debe seleccionar una sucursal suministradora válida."))
        if warehouse.company_id != pos_config.company_id:
            raise AccessError(_("La sucursal suministradora pertenece a otra compañía."))
        pos_warehouse = pos_config._ferreteria_transfer_warehouse()
        if warehouse == pos_warehouse:
            raise ValidationError(
                _("La sucursal solicitante y la suministradora deben ser distintas.")
            )
        return warehouse

    @api.model
    def _pos_recent_requests_payload(self, pos_config, limit=20):
        requests = self.search(
            [
                ("requesting_pos_id", "=", pos_config.id),
                ("requester_id", "=", self.env.user.id),
                ("company_id", "=", pos_config.company_id.id),
            ],
            order="request_date desc, id desc",
            limit=min(max(int(limit or 20), 1), 50),
        )
        state_labels = dict(self._fields["state"].selection)
        return [
            {
                "id": request.id,
                "name": request.name,
                "request_date": fields.Datetime.to_string(request.request_date),
                "supplying_warehouse": request.supplying_warehouse_id.display_name,
                "state": request.state,
                "state_label": state_labels.get(request.state, request.state),
                "requested_qty": request.requested_qty_total,
                "approved_qty": request.approved_qty_total,
                "dispatched_qty": request.dispatched_qty_total,
                "received_qty": request.received_qty_total,
                "line_count": request.line_count,
                "has_incident": bool(request.incident_count),
            }
            for request in requests
        ]

    @api.model
    def pos_get_request_ui_data(self, pos_config_id):
        """Initial data for the POS request dialog."""
        pos_config = self._pos_validate_request_context(pos_config_id)
        pos_warehouse = pos_config._ferreteria_transfer_warehouse()
        warehouses = self.env["stock.warehouse"].search(
            [
                ("company_id", "=", pos_config.company_id.id),
                ("id", "!=", pos_warehouse.id),
            ],
            order="name, id",
        )
        return {
            "pos_config_id": pos_config.id,
            "pos_config_name": pos_config.display_name,
            "requesting_warehouse_id": pos_warehouse.id,
            "requesting_warehouse_name": pos_warehouse.display_name,
            "supplying_warehouses": [
                {"id": warehouse.id, "name": warehouse.display_name}
                for warehouse in warehouses
            ],
            "recent_requests": self._pos_recent_requests_payload(pos_config),
        }

    @api.model
    def pos_search_request_products(
        self, pos_config_id, supplying_warehouse_id, search_term="", limit=40
    ):
        """Return ranked product matches and informative free stock for a branch."""
        pos_config = self._pos_validate_request_context(pos_config_id)
        warehouse = self._pos_validate_supplying_warehouse(
            pos_config, supplying_warehouse_id
        )
        safe_limit = min(max(int(limit or 40), 1), 80)
        term = (search_term or "").strip()
        normalized_term = term.casefold()
        domain = [
            ("active", "=", True),
            ("is_storable", "=", True),
            ("company_id", "in", [False, pos_config.company_id.id]),
        ]
        if term:
            domain += [
                "|",
                "|",
                ("name", "ilike", term),
                ("default_code", "ilike", term),
                ("barcode", "ilike", term),
            ]

        # Fetch a wider candidate set and rank exact codes/barcodes and prefixes first.
        candidate_limit = min(max(safe_limit * 4, safe_limit), 320)
        products = self.env["product.product"].search(
            domain, order="name, default_code, id", limit=candidate_limit
        )

        def _normalized(value):
            return (value or "").strip().casefold()

        def _rank(product):
            code = _normalized(product.default_code)
            barcode = _normalized(product.barcode)
            name = _normalized(
                product.with_context(display_default_code=False).display_name
            )
            if not normalized_term:
                return (7, name, code, product.id)
            if barcode == normalized_term:
                return (0, name, code, product.id)
            if code == normalized_term:
                return (1, name, code, product.id)
            if name == normalized_term:
                return (2, name, code, product.id)
            if code.startswith(normalized_term):
                return (3, name, code, product.id)
            if barcode.startswith(normalized_term):
                return (4, name, code, product.id)
            if name.startswith(normalized_term):
                return (5, name, code, product.id)
            return (6, name, code, product.id)

        products = products.sorted(key=_rank)[:safe_limit]
        exact_code_or_barcode = products.filtered(
            lambda product: normalized_term
            and normalized_term
            in {
                _normalized(product.default_code),
                _normalized(product.barcode),
            }
        )
        exact_match_id = (
            exact_code_or_barcode.id if len(exact_code_or_barcode) == 1 else False
        )

        result = []
        for product in products:
            free_qty = product.with_context(warehouse_id=warehouse.id).free_qty
            result.append(
                {
                    "id": product.id,
                    "name": product.with_context(
                        display_default_code=False
                    ).display_name,
                    "default_code": product.default_code or "",
                    "barcode": product.barcode or "",
                    "uom_id": product.uom_id.id,
                    "uom_name": product.uom_id.display_name,
                    "uom_rounding": product.uom_id.rounding,
                    "tracking": product.tracking,
                    "available_qty": float_round(
                        free_qty,
                        precision_rounding=product.uom_id.rounding,
                    ),
                }
            )
        return {
            "warehouse_id": warehouse.id,
            "warehouse_name": warehouse.display_name,
            "products": result,
            "limit": safe_limit,
            "exact_match_id": exact_match_id,
        }

    @api.model
    def pos_search_request_partners(self, pos_config_id, search_term="", limit=30):
        """Search existing contacts without creating them from the POS dialog."""
        pos_config = self._pos_validate_request_context(pos_config_id)
        safe_limit = min(max(int(limit or 30), 1), 50)
        term = (search_term or "").strip()
        domain = [
            ("active", "=", True),
            ("company_id", "in", [False, pos_config.company_id.id]),
        ]
        if term:
            domain += [
                "|",
                "|",
                "|",
                ("name", "ilike", term),
                ("ref", "ilike", term),
                ("phone", "ilike", term),
                ("email", "ilike", term),
            ]
        partners = self.env["res.partner"].search(
            domain, order="name, id", limit=safe_limit
        )
        return [
            {
                "id": partner.id,
                "name": partner.display_name,
                "ref": partner.ref or "",
                "phone": partner.phone or partner.mobile or "",
            }
            for partner in partners
        ]

    @api.model
    def pos_get_recent_requests(self, pos_config_id, limit=20):
        pos_config = self._pos_validate_request_context(pos_config_id)
        return self._pos_recent_requests_payload(pos_config, limit=limit)

    @api.model
    def pos_create_request_from_ui(self, pos_config_id, payload):
        """Create and submit a request atomically from the POS UI."""
        pos_config = self._pos_validate_request_context(pos_config_id)
        if not isinstance(payload, dict):
            raise UserError(_("No se recibió una solicitud válida desde el POS."))
        warehouse = self._pos_validate_supplying_warehouse(
            pos_config, payload.get("supplying_warehouse_id")
        )

        raw_lines = payload.get("lines") or []
        if not isinstance(raw_lines, list) or not raw_lines:
            raise UserError(_("Debe agregar al menos un producto a la solicitud."))
        if len(raw_lines) > 200:
            raise UserError(_("Una solicitud no puede contener más de 200 líneas."))

        quantities_by_product = {}
        notes_by_product = {}
        for raw_line in raw_lines:
            if not isinstance(raw_line, dict):
                raise UserError(_("Una de las líneas recibidas no es válida."))
            try:
                product_id = int(raw_line.get("product_id") or 0)
                qty = float(raw_line.get("qty") or 0.0)
            except (TypeError, ValueError):
                raise UserError(_("Una línea contiene un producto o cantidad inválidos."))
            if not product_id or not isfinite(qty) or qty <= 0:
                raise UserError(_("Todas las cantidades solicitadas deben ser mayores que cero."))
            quantities_by_product[product_id] = quantities_by_product.get(product_id, 0.0) + qty
            note = (raw_line.get("note") or "").strip()
            if note:
                notes_by_product[product_id] = note[:255]

        products = self.env["product.product"].browse(
            list(quantities_by_product)
        ).exists()
        if len(products) != len(quantities_by_product):
            raise UserError(_("Uno o más productos ya no existen."))
        invalid_products = products.filtered(
            lambda product: not product.active
            or not product.is_storable
            or product.company_id
            and product.company_id != pos_config.company_id
        )
        if invalid_products:
            raise UserError(
                _(
                    "Solo pueden solicitarse productos almacenables activos de la compañía: %s",
                    ", ".join(invalid_products.mapped("display_name")),
                )
            )

        partner_id = int(payload.get("partner_id") or 0)
        partner = self.env["res.partner"].browse(partner_id).exists()
        if partner_id and not partner:
            raise UserError(_("El cliente seleccionado ya no existe."))
        if partner and partner.company_id and partner.company_id != pos_config.company_id:
            raise AccessError(_("El cliente seleccionado pertenece a otra compañía."))

        line_commands = []
        for product in products.sorted(key=lambda item: item.display_name or ""):
            requested_qty = quantities_by_product[product.id]
            if not isfinite(requested_qty) or requested_qty <= 0:
                raise UserError(_("La cantidad solicitada no es válida."))
            line_commands.append(
                Command.create(
                    {
                        "product_id": product.id,
                        "product_uom_id": product.uom_id.id,
                        "requested_qty": requested_qty,
                        "note": notes_by_product.get(product.id),
                    }
                )
            )

        pos_warehouse = pos_config._ferreteria_transfer_warehouse()
        request = self.create(
            {
                "requesting_pos_id": pos_config.id,
                "requesting_warehouse_id": pos_warehouse.id,
                "supplying_warehouse_id": warehouse.id,
                "partner_id": partner.id if partner else False,
                "request_note": (payload.get("request_note") or "").strip(),
                "line_ids": line_commands,
            }
        )
        request.action_submit()
        return {
            "request_id": request.id,
            "request_name": request.name,
            "state": request.state,
            "state_label": dict(self._fields["state"].selection).get(
                request.state, request.state
            ),
            "recent_requests": self._pos_recent_requests_payload(pos_config),
        }
