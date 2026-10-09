# Copyright 2026 Ferretería JD. LGPL-3.
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    is_pos_created = fields.Boolean(
        string="Creada desde punto de venta", default=False, copy=False, readonly=True
    )
    ferreteria_pos_config_id = fields.Many2one(
        "pos.config", string="POS de origen", readonly=True, copy=False, index=True
    )
    ferreteria_pos_invoice_ids = fields.One2many(
        "account.move", "ferreteria_pos_sale_order_id",
        string="Facturas generadas en POS", readonly=True,
    )
    ferreteria_pos_invoice_count = fields.Integer(
        string="Facturas POS", compute="_compute_ferreteria_pos_invoice_count"
    )

    @api.depends("ferreteria_pos_invoice_ids", "ferreteria_pos_invoice_ids.state")
    def _compute_ferreteria_pos_invoice_count(self):
        for order in self:
            order.ferreteria_pos_invoice_count = len(
                order.ferreteria_pos_invoice_ids.filtered(
                    lambda invoice: invoice.state != "cancel"
                )
            )

    def action_view_ferreteria_pos_invoices(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Factura del punto de venta"),
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [
                ("ferreteria_pos_sale_order_id", "=", self.id),
                ("move_type", "=", "out_invoice"),
            ],
            "context": {"create": False},
        }

    @api.model
    def _load_pos_data_fields(self, config_id):
        names = super()._load_pos_data_fields(config_id)
        for field_name in ("is_pos_created", "ferreteria_pos_config_id", "warehouse_id"):
            if field_name not in names:
                names.append(field_name)
        return names

    @api.model
    def create_quotation_from_pos(
        self, partner_id, items, pos_config_id, pricelist_id=False,
        fiscal_position_id=False,
    ):
        """Crear cotización con el almacén de la operación de salida del POS."""
        if not self.env.user.has_group("point_of_sale.group_pos_user"):
            raise AccessError(_("Solo un usuario de punto de venta puede crear cotizaciones."))
        config = self.env["pos.config"].browse(int(pos_config_id)).exists()
        if not config or not config.create_so:
            raise UserError(_("La creación de cotizaciones está deshabilitada para este POS."))
        session = self.env["pos.session"].search([
            ("config_id", "=", config.id),
            ("user_id", "=", self.env.uid),
            ("state", "=", "opened"),
        ], limit=1)
        if not session:
            raise UserError(_("Necesita una sesión de POS abierta para generar la cotización."))
        warehouse = config.picking_type_id.warehouse_id
        if not warehouse or warehouse.company_id != config.company_id:
            raise UserError(_(
                "El tipo de operación del POS no tiene un almacén válido de la misma empresa."
            ))
        partner = self.env["res.partner"].browse(int(partner_id)).exists()
        if not partner or (partner.company_id and partner.company_id != config.company_id):
            raise UserError(_("Seleccione un cliente válido de esta empresa."))
        if not isinstance(items, list) or not items:
            raise UserError(_("La cotización debe contener al menos un producto."))

        lines = []
        for item in items:
            if not isinstance(item, dict):
                raise UserError(_("Hay productos con datos incorrectos."))
            product = self.env["product.product"].browse(int(item.get("product_id") or 0)).exists()
            if not product or not product.sale_ok or (
                product.company_id and product.company_id != config.company_id
            ):
                raise UserError(_("Hay un producto que no se puede vender en esta empresa."))
            try:
                quantity = float(item.get("quantity") or 0)
                price = float(item.get("price_unit") or 0)
                discount = float(item.get("discount") or 0)
            except (ValueError, TypeError):
                raise UserError(_("Revise cantidades, precios y descuentos."))
            if quantity <= 0 or price < 0 or not 0 <= discount <= 100:
                raise UserError(_("Cantidad, precio o descuento fuera de rango."))
            lines.append(fields.Command.create({
                "product_id": product.id,
                "name": product.get_product_multiline_description_sale() or product.display_name,
                "product_uom": product.uom_id.id,
                "product_uom_qty": quantity,
                "price_unit": price,
                "discount": discount,
            }))

        pricelist = (
            self.env["product.pricelist"].browse(int(pricelist_id)).exists()
            if pricelist_id else config.pricelist_id
        )
        fiscal_position = (
            self.env["account.fiscal.position"].browse(int(fiscal_position_id)).exists()
            if fiscal_position_id else False
        )
        if pricelist and pricelist.company_id and pricelist.company_id != config.company_id:
            raise UserError(_("La tarifa pertenece a otra empresa."))
        if fiscal_position and fiscal_position.company_id and fiscal_position.company_id != config.company_id:
            raise UserError(_("La posición fiscal pertenece a otra empresa."))

        values = {
            "partner_id": partner.id,
            "company_id": config.company_id.id,
            "warehouse_id": warehouse.id,
            "ferreteria_pos_config_id": config.id,
            "is_pos_created": True,
            "order_line": lines,
        }
        if pricelist:
            values["pricelist_id"] = pricelist.id
        if fiscal_position:
            values["fiscal_position_id"] = fiscal_position.id

        order = self.with_company(config.company_id).create(values)
        return {
            "id": order.id,
            "name": order.name,
            "warehouse": warehouse.display_name,
        }

    def ferreteria_validate_pos_checkout(self, pos_config_id):
        """Validar antes de importar al POS. No confirma ni factura la venta."""
        self.ensure_one()
        if not self.env.user.has_group("point_of_sale.group_pos_user"):
            raise AccessError(_("No tiene permiso para cobrar desde POS."))
        config = self.env["pos.config"].browse(int(pos_config_id)).exists()
        if not config or not config.create_so:
            raise UserError(_("POS sin autorización para procesar cotizaciones."))
        if not self.is_pos_created:
            raise UserError(_("Utilice el cobro estándar para pedidos externos al POS."))
        if self.state not in ("draft", "sent"):
            raise UserError(_("La cotización ya fue confirmada o cancelada."))
        if self.company_id != config.company_id:
            raise UserError(_("La cotización pertenece a otra empresa."))
        if self.warehouse_id != config.picking_type_id.warehouse_id:
            raise UserError(_(
                "El almacén de la cotización (%(sale)s) no corresponde al POS (%(pos)s). "
                "Corrija el almacén en Ventas antes de cobrar.",
                sale=self.warehouse_id.display_name,
                pos=config.picking_type_id.warehouse_id.display_name,
            ))
        if self.ferreteria_pos_config_id and self.ferreteria_pos_config_id != config:
            raise UserError(_("Esta cotización se creó en otro punto de venta."))
        session = self.env["pos.session"].search_count([
            ("config_id", "=", config.id),
            ("user_id", "=", self.env.uid),
            ("state", "=", "opened"),
        ])
        if not session:
            raise UserError(_("Necesita una sesión abierta en este punto de venta."))
        if self.order_line.mapped("invoice_lines").filtered(
            lambda line: line.move_id.state != "cancel"
        ):
            raise UserError(_("La cotización ya tiene una factura de Ventas. No vuelva a cobrarla."))
        if self.ferreteria_pos_invoice_ids.filtered(lambda inv: inv.state != "cancel"):
            raise UserError(_("La cotización ya tiene una factura POS. No puede facturarse otra vez."))
        if self.pos_order_line_ids.mapped("order_id").filtered(
            lambda pos: pos.state in ("paid", "done", "invoiced")
        ):
            raise UserError(_("La cotización ya tiene una venta cobrada desde otro POS."))
        return {"id": self.id, "name": self.name, "warehouse": self.warehouse_id.display_name}

    def pos_send_quotation_email(self):
        """Envía cotización y su PDF con la plantilla estándar de Ventas."""
        self.ensure_one()
        if not self.env.user.has_group("point_of_sale.group_pos_user"):
            raise AccessError(_("No tiene permisos para enviar cotizaciones desde el POS."))
        if self.state not in ("draft", "sent"):
            raise UserError(_("Solo se pueden enviar cotizaciones sin confirmar."))
        if not self.partner_id.email:
            raise UserError(_("El cliente no tiene un correo electrónico configurado."))
        template = self.env.ref("sale.email_template_edi_sale", raise_if_not_found=False)
        if not template:
            raise UserError(_("No se encontró la plantilla de correo para cotizaciones."))
        template.send_mail(
            self.id,
            force_send=True,
            raise_exception=True,
            email_values={"email_to": self.partner_id.email},
        )
        if self.state == "draft":
            self.action_quotation_sent()
        return True
