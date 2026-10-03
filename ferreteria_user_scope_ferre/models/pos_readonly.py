from odoo import _, api, models
from odoo.exceptions import AccessError


class PosReadonlyMixin(models.AbstractModel):
    _name = "ferreteria.pos.readonly.mixin"
    _description = "Protección servidor para POS solo consulta"

    @api.model
    def _ferreteria_is_pos_readonly(self):
        return (
            not self.env.su
            and self.env.user.has_group(
                "ferreteria_user_scope_ferre.group_pos_readonly"
            )
        )

    @api.model
    def _ferreteria_deny_pos_mutation(self):
        if self._ferreteria_is_pos_readonly():
            raise AccessError(
                _("Su perfil Punto de Venta: solo consulta no permite esta operación.")
            )


class PosOrder(models.Model):
    _inherit = ["pos.order", "ferreteria.pos.readonly.mixin"]
    _name = "pos.order"

    @api.model_create_multi
    def create(self, vals_list):
        self._ferreteria_deny_pos_mutation()
        return super().create(vals_list)

    def write(self, vals):
        self._ferreteria_deny_pos_mutation()
        return super().write(vals)

    def unlink(self):
        self._ferreteria_deny_pos_mutation()
        return super().unlink()

    def refund(self):
        self._ferreteria_deny_pos_mutation()
        return super().refund()

    def action_pos_order_cancel(self):
        self._ferreteria_deny_pos_mutation()
        return super().action_pos_order_cancel()


class PosOrderLine(models.Model):
    _inherit = ["pos.order.line", "ferreteria.pos.readonly.mixin"]
    _name = "pos.order.line"

    @api.model_create_multi
    def create(self, vals_list):
        self._ferreteria_deny_pos_mutation()
        return super().create(vals_list)

    def write(self, vals):
        self._ferreteria_deny_pos_mutation()
        return super().write(vals)

    def unlink(self):
        self._ferreteria_deny_pos_mutation()
        return super().unlink()


class PosPayment(models.Model):
    _inherit = ["pos.payment", "ferreteria.pos.readonly.mixin"]
    _name = "pos.payment"

    @api.model_create_multi
    def create(self, vals_list):
        self._ferreteria_deny_pos_mutation()
        return super().create(vals_list)

    def write(self, vals):
        self._ferreteria_deny_pos_mutation()
        return super().write(vals)

    def unlink(self):
        self._ferreteria_deny_pos_mutation()
        return super().unlink()


class PosSession(models.Model):
    _inherit = ["pos.session", "ferreteria.pos.readonly.mixin"]
    _name = "pos.session"

    @api.model_create_multi
    def create(self, vals_list):
        self._ferreteria_deny_pos_mutation()
        return super().create(vals_list)

    def write(self, vals):
        self._ferreteria_deny_pos_mutation()
        return super().write(vals)

    def unlink(self):
        self._ferreteria_deny_pos_mutation()
        return super().unlink()

    def action_pos_session_open(self):
        self._ferreteria_deny_pos_mutation()
        return super().action_pos_session_open()

    def action_pos_session_closing_control(self, *args, **kwargs):
        self._ferreteria_deny_pos_mutation()
        return super().action_pos_session_closing_control(*args, **kwargs)

    def action_pos_session_validate(self, *args, **kwargs):
        self._ferreteria_deny_pos_mutation()
        return super().action_pos_session_validate(*args, **kwargs)

    def action_pos_session_close(self, *args, **kwargs):
        self._ferreteria_deny_pos_mutation()
        return super().action_pos_session_close(*args, **kwargs)

    def close_session_from_ui(self, *args, **kwargs):
        self._ferreteria_deny_pos_mutation()
        return super().close_session_from_ui(*args, **kwargs)


class PosConfig(models.Model):
    _inherit = ["pos.config", "ferreteria.pos.readonly.mixin"]
    _name = "pos.config"

    @api.model_create_multi
    def create(self, vals_list):
        self._ferreteria_deny_pos_mutation()
        return super().create(vals_list)

    def write(self, vals):
        self._ferreteria_deny_pos_mutation()
        return super().write(vals)

    def unlink(self):
        self._ferreteria_deny_pos_mutation()
        return super().unlink()

    def open_ui(self):
        self._ferreteria_deny_pos_mutation()
        return super().open_ui()

    def open_existing_session_cb(self):
        self._ferreteria_deny_pos_mutation()
        return super().open_existing_session_cb()
