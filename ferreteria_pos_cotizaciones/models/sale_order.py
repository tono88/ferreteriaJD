# Copyright 2026 Ferretería JD. LGPL-3.
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    is_pos_created = fields.Boolean(
        string="Creada desde punto de venta", default=False, copy=False, readonly=True
    )

    @api.model
    def create_quotation_from_pos(self, partner_id, items, pos_config_id):
        """Construye la cotización mediante la API estándar; Odoo calcula los impuestos."""
        if not self.env.user.has_group("point_of_sale.group_pos_user"):
            raise AccessError(_("Solo un usuario de punto de venta puede crear cotizaciones."))
        config = self.env["pos.config"].browse(int(pos_config_id)).exists()
        if not config or not config.create_so:
            raise UserError(_("La creación de cotizaciones está deshabilitada para este POS."))
        open_session = self.env["pos.session"].search_count([
            ("config_id", "=", config.id),
            ("user_id", "=", self.env.uid),
            ("state", "=", "opened"),
        ])
        if not open_session:
            raise UserError(_("Necesita una sesión de POS abierta para generar la cotización."))
        partner = self.env["res.partner"].browse(int(partner_id)).exists()
        if not partner:
            raise UserError(_("Seleccione un cliente válido."))
        if not isinstance(items, list) or not items:
            raise UserError(_("La cotización debe contener al menos un producto."))

        lines = []
        for item in items:
            if not isinstance(item, dict):
                raise UserError(_("Hay productos con datos incorrectos."))
            product = self.env["product.product"].browse(int(item.get("product_id") or 0)).exists()
            if not product or not product.sale_ok:
                raise UserError(_("Hay un producto que no se puede vender."))
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
        order = self.with_company(config.company_id).create({
            "partner_id": partner.id,
            "company_id": config.company_id.id,
            "is_pos_created": True,
            "order_line": lines,
        })
        return {"id": order.id, "name": order.name}

    def pos_send_quotation_email(self):
        """Envía la plantilla estándar de venta, con PDF adjunto, al correo del cliente."""
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
