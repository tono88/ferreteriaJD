# Copyright 2026 Ferretería JD
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import hashlib
import hmac
import secrets
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class PosDiscountOtp(models.Model):
    _name = "pos.discount.otp"
    _description = "Código de autorización de descuento del POS"
    _order = "create_date desc"

    employee_id = fields.Many2one("hr.employee", string="Cajero", required=True, readonly=True)
    config_id = fields.Many2one("pos.config", string="Punto de venta", required=True, readonly=True)
    issued_by = fields.Many2one("res.users", string="Generado por", readonly=True)
    expires_at = fields.Datetime(string="Vence", required=True, readonly=True)
    used_at = fields.Datetime(string="Utilizado el", readonly=True)
    failed_attempts = fields.Integer(string="Intentos fallidos", readonly=True, default=0)
    salt = fields.Char(string="Sal", readonly=True, groups="base.group_system")
    code_hash = fields.Char(string="Hash", readonly=True, groups="base.group_system")
    order_reference = fields.Char(string="Referencia de venta", readonly=True)

    @staticmethod
    def _digest(code, salt):
        return hashlib.pbkdf2_hmac(
            "sha256", str(code).encode("utf-8"), bytes.fromhex(salt), 100_000
        ).hex()

    @api.model
    def _issue_code(self, employee, config):
        """Solo gerentes: entrega el código una vez; persiste únicamente su hash."""
        if not self.env.user.has_group("point_of_sale.group_pos_manager"):
            raise AccessError(_("Solo un gerente del punto de venta puede generar códigos."))
        employee.ensure_one()
        config.ensure_one()
        if not employee.active or (employee.company_id and employee.company_id != config.company_id):
            raise UserError(_("El cajero no está activo o pertenece a otra compañía."))
        now = fields.Datetime.now()
        # Revocar cualquier código anterior para ese cajero y POS.
        old_codes = self.sudo().search([
            ("employee_id", "=", employee.id),
            ("config_id", "=", config.id),
            ("used_at", "=", False),
        ])
        old_codes.write({"used_at": now})
        code = str(secrets.randbelow(900000) + 100000)  # Nunca empieza con cero.
        salt = secrets.token_hex(16)
        expiry = now + timedelta(minutes=10)
        self.sudo().create({
            "employee_id": employee.id,
            "config_id": config.id,
            "issued_by": self.env.uid,
            "expires_at": expiry,
            "salt": salt,
            "code_hash": self._digest(code, salt),
        })
        return code, expiry

    @api.model
    def consume_code(self, code, cashier_id, pos_config_id, order_reference=None):
        """Operación atómica: el mismo código jamás autoriza dos operaciones."""
        if not self.env.user.has_group("point_of_sale.group_pos_user"):
            raise AccessError(_("No tiene acceso a los puntos de venta."))
        try:
            employee_id = int(cashier_id)
            config_id = int(pos_config_id)
        except (ValueError, TypeError):
            return {"approved": False, "message": _("Datos de autorización inválidos.")}

        # El código no puede utilizarse desde un POS distinto ni una sesión ajena.
        active_session = self.env["pos.session"].sudo().search_count([
            ("config_id", "=", config_id),
            ("user_id", "=", self.env.uid),
            ("state", "=", "opened"),
        ])
        if not active_session:
            return {"approved": False, "message": _("No existe una sesión abierta para este usuario y POS.")}

        token = self.sudo().search([
            ("employee_id", "=", employee_id),
            ("config_id", "=", config_id),
            ("used_at", "=", False),
        ], limit=1, order="id desc")
        if not token:
            return {"approved": False, "message": _("Código inválido, utilizado o no generado.")}

        # Bloqueo de fila antes de verificar y consumir: evita doble uso concurrente.
        self.env.cr.execute("SELECT id FROM pos_discount_otp WHERE id = %s FOR UPDATE", [token.id])
        token.invalidate_recordset(["used_at", "failed_attempts", "expires_at", "code_hash", "salt"])
        now = fields.Datetime.now()
        if token.used_at or token.expires_at <= now:
            return {"approved": False, "message": _("El código ya fue utilizado o venció.")}
        if token.failed_attempts >= 5:
            return {"approved": False, "message": _("Código bloqueado por demasiados intentos.")}
        valid_format = isinstance(code, (str, int)) and str(code).isdigit() and len(str(code)) == 6
        valid_code = valid_format and hmac.compare_digest(
            self._digest(str(code), token.salt), token.code_hash
        )
        if not valid_code:
            token.write({
                "failed_attempts": token.failed_attempts + 1,
                **({"used_at": now} if token.failed_attempts >= 4 else {}),
            })
            return {"approved": False, "message": _("Código incorrecto.")}
        token.write({
            "used_at": now,
            "order_reference": str(order_reference or "")[:128],
        })
        return {"approved": True, "message": _("Descuento autorizado.")}
