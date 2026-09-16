from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResUsers(models.Model):
    _inherit = "res.users"

    ferreteria_scope_enforced = fields.Boolean(
        string="Restringir por POS y almacén",
        default=False,
        help=(
            "Aplica reglas globales de servidor para limitar POS, ventas e inventario "
            "a los POS y almacenes autorizados. Déjelo desactivado para administradores."
        ),
    )
    ferreteria_allowed_pos_ids = fields.Many2many(
        "pos.config",
        "ferreteria_user_allowed_pos_rel",
        "user_id",
        "pos_config_id",
        string="POS permitidos",
        check_company=False,
    )
    ferreteria_allowed_warehouse_ids = fields.Many2many(
        "stock.warehouse",
        "ferreteria_user_allowed_warehouse_rel",
        "user_id",
        "warehouse_id",
        string="Almacenes permitidos",
        check_company=False,
    )
    ferreteria_sales_readonly = fields.Boolean(
        string="Ventas solo consulta",
        default=False,
        help="Bloquea en servidor crear, editar y eliminar pedidos y líneas de venta.",
    )
    ferreteria_interbranch_transit_location_id = fields.Many2one(
        "stock.location",
        string="Ubicación técnica de tránsito intersucursal",
        compute="_compute_ferreteria_interbranch_transit_location",
        compute_sudo=True,
        help=(
            "Referencia técnica obtenida por XML-ID para permitir al motor de stock "
            "consumir reservas legítimas en la ubicación compartida de tránsito."
        ),
    )

    def _compute_ferreteria_interbranch_transit_location(self):
        transit_location = self.env.ref(
            "ferreteria_pos_transfer_request_ferre.location_interbranch_transit",
            raise_if_not_found=False,
        )
        for user in self:
            user.ferreteria_interbranch_transit_location_id = transit_location

    @api.constrains(
        "ferreteria_scope_enforced",
        "ferreteria_allowed_pos_ids",
        "ferreteria_allowed_warehouse_ids",
    )
    def _check_ferreteria_operational_scope(self):
        for user in self:
            if not user.ferreteria_scope_enforced:
                continue
            if not user.ferreteria_allowed_warehouse_ids:
                raise ValidationError(_("Debe asignar al menos un almacén permitido."))
            pos_warehouses = user.ferreteria_allowed_pos_ids.mapped(
                "picking_type_id.warehouse_id"
            ) | user.ferreteria_allowed_pos_ids.mapped("warehouse_id")
            outside = pos_warehouses - user.ferreteria_allowed_warehouse_ids
            if outside:
                raise ValidationError(
                    _(
                        "Cada POS permitido debe pertenecer a un almacén permitido. "
                        "Fuera del ámbito: %s"
                    )
                    % ", ".join(outside.mapped("display_name"))
                )
