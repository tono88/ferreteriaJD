# Copyright 2026 Ferretería JD
# License AGPL-3.0 or later.
from markupsafe import escape

from odoo import _, fields, models
from odoo.exceptions import AccessError, UserError


class PosDiscountOtpWizard(models.TransientModel):
    _name = "pos.discount.otp.wizard"
    _description = "Generar código de descuento para el cajero"

    employee_id = fields.Many2one("hr.employee", string="Cajero", required=True)
    config_id = fields.Many2one("pos.config", string="Punto de venta", required=True)
    generated_code = fields.Char(string="Código para compartir", readonly=True)
    expires_at = fields.Datetime(string="Válido hasta", readonly=True)

    def _check_manager(self):
        if not self.env.user.has_group("point_of_sale.group_pos_manager"):
            raise AccessError(_("Solo los gerentes pueden generar y enviar códigos."))

    def action_generate(self):
        self.ensure_one()
        self._check_manager()
        code, expiry = self.env["pos.discount.otp"]._issue_code(
            self.employee_id, self.config_id
        )
        self.write({"generated_code": code, "expires_at": expiry})
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_send_email(self):
        self.ensure_one()
        self._check_manager()
        if not self.generated_code or self.expires_at <= fields.Datetime.now():
            raise UserError(_("Primero genere un código válido."))
        if not self.employee_id.work_email:
            raise UserError(_("El cajero no tiene correo de trabajo configurado."))
        subject = _("Autorización de descuento de un solo uso")
        body = _(
            "<p>Su código para el POS <b>%(pos)s</b> es <b>%(code)s</b>.</p>"
            "<p>Vence el %(expiry)s. Solo puede utilizarse una vez.</p>",
            pos=escape(self.config_id.name),
            code=escape(self.generated_code),
            expiry=escape(str(self.expires_at)),
        )
        self.env["mail.mail"].sudo().create({
            "email_to": self.employee_id.work_email,
            "subject": subject,
            "body_html": body,
        }).send(raise_exception=True)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Código enviado"),
                "message": _("Se envió al correo laboral del cajero."),
                "type": "success",
                "sticky": False,
            },
        }
