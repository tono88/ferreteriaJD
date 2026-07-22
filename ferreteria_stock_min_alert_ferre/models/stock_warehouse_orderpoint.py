# -*- coding: utf-8 -*-

import logging

from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.tools import float_compare


_logger = logging.getLogger(__name__)


class StockWarehouseOrderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    ferreteria_min_alert_active = fields.Boolean(
        string="Alerta de mínimo activa",
        default=False,
        copy=False,
        readonly=True,
        help=(
            "Indica que ya se envió la alerta correspondiente al ciclo actual por "
            "debajo del mínimo. Se reinicia automáticamente cuando el inventario "
            "pronosticado vuelve al mínimo o lo supera."
        ),
    )
    ferreteria_min_alert_last_notified_at = fields.Datetime(
        string="Última alerta enviada",
        copy=False,
        readonly=True,
    )
    ferreteria_min_alert_last_resolved_at = fields.Datetime(
        string="Última alerta resuelta",
        copy=False,
        readonly=True,
    )
    ferreteria_min_alert_notification_count = fields.Integer(
        string="Alertas enviadas",
        default=0,
        copy=False,
        readonly=True,
    )
    ferreteria_min_alert_mail_id = fields.Many2one(
        "mail.mail",
        string="Último correo generado",
        copy=False,
        readonly=True,
        ondelete="set null",
    )

    def _ferreteria_is_below_minimum(self):
        self.ensure_one()
        if (
            not self.active
            or not self.product_id
            or not self.location_id
            or self.product_min_qty <= 0
        ):
            return False
        rounding = self.product_uom.rounding or 0.01
        return (
            float_compare(
                self.qty_forecast,
                self.product_min_qty,
                precision_rounding=rounding,
            )
            < 0
        )

    def _ferreteria_stock_alert_recipients(self):
        self.ensure_one()
        domain = [
            ("active", "=", True),
            ("share", "=", False),
            ("ferreteria_receive_stock_min_alerts", "=", True),
            ("partner_id.email", "!=", False),
        ]
        if self.company_id:
            domain.append(("company_ids", "in", self.company_id.id))
        users = self.env["res.users"].sudo().search(domain)
        return users.mapped("partner_id").filtered(lambda partner: partner.email)

    def _ferreteria_replenishment_url(self):
        self.ensure_one()
        base_url = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("web.base.url", "")
            .rstrip("/")
        )
        return f"{base_url}/odoo/action-stock.action_orderpoint_replenish/{self.id}"

    def _ferreteria_product_label(self):
        self.ensure_one()
        code = (self.product_id.default_code or "").strip()
        name = self.product_id.display_name or self.product_id.name or ""
        if code and not name.startswith(f"[{code}]"):
            return f"[{code}] {name}"
        return name

    def _ferreteria_create_stock_alert_mail(self, recipients):
        self.ensure_one()
        product_label = self._ferreteria_product_label()
        warehouse_name = self.warehouse_id.display_name or _("Sin almacén")
        location_name = self.location_id.display_name or _("Sin ubicación")
        uom_name = self.product_uom.display_name or ""
        replenishment_url = self._ferreteria_replenishment_url()

        subject = _(
            "[Reabastecimiento] %(product)s - %(warehouse)s",
            product=product_label,
            warehouse=warehouse_name,
        )

        body_html = Markup(
            """
            <div style="font-family:Arial,Helvetica,sans-serif;font-size:14px;color:#222;line-height:1.5;">
                <h2 style="margin:0 0 12px;color:#7c5ca4;">Alerta de reabastecimiento</h2>
                <p>El inventario pronosticado del siguiente producto quedó por debajo del mínimo configurado:</p>
                <table style="border-collapse:collapse;width:100%%;max-width:680px;">
                    <tr><td style="padding:6px;border-bottom:1px solid #ddd;"><strong>Producto</strong></td><td style="padding:6px;border-bottom:1px solid #ddd;">%s</td></tr>
                    <tr><td style="padding:6px;border-bottom:1px solid #ddd;"><strong>Almacén</strong></td><td style="padding:6px;border-bottom:1px solid #ddd;">%s</td></tr>
                    <tr><td style="padding:6px;border-bottom:1px solid #ddd;"><strong>Ubicación</strong></td><td style="padding:6px;border-bottom:1px solid #ddd;">%s</td></tr>
                    <tr><td style="padding:6px;border-bottom:1px solid #ddd;"><strong>A la mano</strong></td><td style="padding:6px;border-bottom:1px solid #ddd;">%.2f %s</td></tr>
                    <tr><td style="padding:6px;border-bottom:1px solid #ddd;"><strong>Pronóstico</strong></td><td style="padding:6px;border-bottom:1px solid #ddd;">%.2f %s</td></tr>
                    <tr><td style="padding:6px;border-bottom:1px solid #ddd;"><strong>Mínimo</strong></td><td style="padding:6px;border-bottom:1px solid #ddd;">%.2f %s</td></tr>
                    <tr><td style="padding:6px;border-bottom:1px solid #ddd;"><strong>Máximo</strong></td><td style="padding:6px;border-bottom:1px solid #ddd;">%.2f %s</td></tr>
                    <tr><td style="padding:6px;border-bottom:1px solid #ddd;"><strong>Por ordenar</strong></td><td style="padding:6px;border-bottom:1px solid #ddd;">%.2f %s</td></tr>
                </table>
                <p style="margin:22px 0;">
                    <a href="%s" style="background:#7c5ca4;color:#fff;text-decoration:none;padding:10px 18px;border-radius:4px;display:inline-block;">
                        Abrir reabastecimiento en Odoo
                    </a>
                </p>
                <p style="font-size:12px;color:#666;">
                    Esta alerta se envía una sola vez mientras el producto permanezca por debajo del mínimo.
                    Si el inventario se recupera y posteriormente vuelve a bajar, se generará una nueva alerta.
                </p>
            </div>
            """
            % (
                escape(product_label),
                escape(warehouse_name),
                escape(location_name),
                self.qty_on_hand,
                escape(uom_name),
                self.qty_forecast,
                escape(uom_name),
                self.product_min_qty,
                escape(uom_name),
                self.product_max_qty,
                escape(uom_name),
                self.qty_to_order,
                escape(uom_name),
                escape(replenishment_url),
            )
        )

        values = {
            "subject": subject,
            "body_html": body_html,
            "recipient_ids": [(6, 0, recipients.ids)],
            "model": self._name,
            "res_id": self.id,
            "auto_delete": False,
        }
        email_from = self.company_id.email or self.env.user.email
        if email_from:
            values["email_from"] = email_from
        if self.company_id.email:
            values["reply_to"] = self.company_id.email

        return self.env["mail.mail"].sudo().create(values)

    def _ferreteria_process_stock_min_alerts(self):
        stats = {
            "sent": 0,
            "resolved": 0,
            "already_active": 0,
            "without_recipients": 0,
        }
        now = fields.Datetime.now()

        for orderpoint in self.sudo():
            below_minimum = orderpoint._ferreteria_is_below_minimum()

            if below_minimum:
                if orderpoint.ferreteria_min_alert_active:
                    stats["already_active"] += 1
                    continue

                recipients = orderpoint._ferreteria_stock_alert_recipients()
                if not recipients:
                    stats["without_recipients"] += 1
                    _logger.warning(
                        "No se envió alerta de reabastecimiento para la regla %s porque no hay usuarios activos con correo y la opción de alertas marcada.",
                        orderpoint.id,
                    )
                    continue

                mail = orderpoint._ferreteria_create_stock_alert_mail(recipients)
                orderpoint.write(
                    {
                        "ferreteria_min_alert_active": True,
                        "ferreteria_min_alert_last_notified_at": now,
                        "ferreteria_min_alert_notification_count": (
                            orderpoint.ferreteria_min_alert_notification_count + 1
                        ),
                        "ferreteria_min_alert_mail_id": mail.id,
                    }
                )
                mail.send_after_commit()
                stats["sent"] += 1
                continue

            if orderpoint.ferreteria_min_alert_active:
                orderpoint.write(
                    {
                        "ferreteria_min_alert_active": False,
                        "ferreteria_min_alert_last_resolved_at": now,
                    }
                )
                stats["resolved"] += 1

        return stats

    @api.model
    def _cron_check_ferreteria_stock_min_alerts(self):
        orderpoints = self.with_context(active_test=False).sudo().search(
            [
                "|",
                ("active", "=", True),
                ("ferreteria_min_alert_active", "=", True),
            ]
        )
        stats = orderpoints._ferreteria_process_stock_min_alerts()
        _logger.info(
            "Revisión de alertas de reabastecimiento finalizada: %s",
            stats,
        )
        return stats

    def action_check_ferreteria_stock_min_alert_now(self):
        self.ensure_one()
        stats = self._ferreteria_process_stock_min_alerts()
        if stats["sent"]:
            message = _("Se generó el correo de alerta y se enviará mediante el servidor SMTP configurado.")
            notification_type = "success"
        elif stats["already_active"]:
            message = _("La alerta ya había sido enviada para el ciclo actual; no se generó un correo duplicado.")
            notification_type = "info"
        elif stats["resolved"]:
            message = _("El inventario ya está en el mínimo o por encima; la alerta quedó resuelta.")
            notification_type = "success"
        elif stats["without_recipients"]:
            message = _("No hay usuarios activos con correo y la opción 'Recibir alertas de reabastecimiento' marcada.")
            notification_type = "warning"
        else:
            message = _("El inventario no está por debajo del mínimo; no se requiere alerta.")
            notification_type = "info"

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Alertas de reabastecimiento"),
                "message": message,
                "type": notification_type,
                "sticky": False,
            },
        }
