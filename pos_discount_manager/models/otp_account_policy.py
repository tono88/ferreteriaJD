# Copyright 2026 Ferretería JD. AGPL-3.0.
"""Compatibilidad del OTP con cajero = usuario autenticado de Odoo.

El empleado se resuelve exclusivamente en el servidor; ningún ID de empleado
aportado por el navegador se utiliza como identidad al canjear un OTP.
"""
from odoo import _, api, models
from odoo.exceptions import AccessError, UserError


class PosDiscountOtp(models.Model):
    _inherit = "pos.discount.otp"

    @api.model
    def get_logged_user_discount_policy(self, pos_config_id):
        if not self.env.user.has_group("point_of_sale.group_pos_user"):
            raise AccessError(_("Su usuario no tiene acceso al punto de venta."))
        try:
            config_id = int(pos_config_id)
        except (ValueError, TypeError):
            raise UserError(_("Identificador de POS inválido."))

        config = self.env["pos.config"].sudo().browse(config_id).exists()
        if not config:
            raise UserError(_("El punto de venta ya no existe."))
        if config.module_pos_hr:
            raise UserError(_(
                "Este POS usa selección de empleados; no corresponde al "
                "modo de cajero por usuario de Odoo."
            ))
        if config.company_id not in self.env.user.company_ids:
            raise AccessError(_("Su usuario no pertenece a la empresa de este POS."))

        # La sesión se comprueba sin delegar derechos: el usuario que está
        # autenticado puede acceder al POS pero no necesariamente fue quien
        # creó la sesión (la apertura puede estar asignada a otra persona).
        opened = self.env["pos.session"].sudo().search_count([
            ("config_id", "=", config.id),
            ("state", "=", "opened"),
        ])
        if not opened:
            raise UserError(_("Este POS no tiene una sesión abierta."))

        employees = self.env["hr.employee"].sudo().search([
            ("user_id", "=", self.env.uid),
            ("company_id", "=", config.company_id.id),
            ("active", "=", True),
        ], limit=2)
        if not employees:
            raise UserError(_(
                "La cuenta de Odoo no tiene un empleado activo asociado en "
                "esta empresa. Asócielo desde Empleados → Ajustes de RR. HH."
            ))
        if len(employees) > 1:
            raise UserError(_(
                "Existen varios empleados activos asociados a esta cuenta en "
                "la misma empresa. Deje un solo empleado para evitar confusiones."
            ))

        employee = employees[0]
        limit = employee.limited_discount
        if limit is None or not 0 <= limit <= 100:
            raise UserError(_("El límite de descuento del empleado no es válido."))
        return {
            "employee_id": employee.id,
            "employee_name": employee.name,
            "limited_discount": limit,
            "pos_config_id": config.id,
        }

    @api.model
    def consume_code_for_logged_user(self, code, pos_config_id, order_reference=None):
        """La identidad proviene de la sesión web, no de campos enviados por JS."""
        policy = self.get_logged_user_discount_policy(pos_config_id)
        # Reutilizar canje transaccional, hash, plazo e invalidación original.
        # consume_code exige una sesión POS abierta por este mismo usuario.
        return self.consume_code(
            code, policy["employee_id"], policy["pos_config_id"], order_reference
        )
