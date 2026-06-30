# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


class FerreteriaTransferUserPermission(models.Model):
    _name = "ferreteria.transfer.user.permission"
    _description = "Permiso de solicitudes entre sucursales por usuario"
    _order = "user_id, id"

    active = fields.Boolean(default=True)
    user_id = fields.Many2one(
        "res.users",
        string="Usuario",
        required=True,
        index=True,
        ondelete="cascade",
        check_company=False,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Compañía de referencia",
        default=lambda self: self.env.company,
        readonly=True,
        index=True,
        help=(
            "Campo técnico conservado para compatibilidad. Los selectores de almacenes "
            "y puntos de venta no se filtran por este valor."
        ),
    )

    warehouse_ids = fields.Many2many(
        "stock.warehouse",
        "ferreteria_transfer_permission_warehouse_rel",
        "permission_id",
        "warehouse_id",
        string="Sucursales / almacenes",
        help=(
            "Seleccione una o varias sucursales. Aprobar, despachar y recibir se "
            "validan contra esta lista."
        ),
    )
    pos_config_ids = fields.Many2many(
        "pos.config",
        "ferreteria_transfer_permission_pos_rel",
        "permission_id",
        "pos_config_id",
        string="Puntos de venta",
        help=(
            "Seleccione uno o varios POS. Para el permiso Solicitar, si esta lista "
            "tiene valores solo se autorizan esos POS. Si queda vacía, el permiso "
            "aplica a todos los POS de las sucursales seleccionadas."
        ),
    )

    # Campos de la versión 18.0.2.2.0 conservados únicamente para migración y
    # compatibilidad con registros ya existentes. Las vistas nuevas no los usan.
    warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Sucursal heredada",
        index=True,
        ondelete="set null",
        check_company=False,
    )
    pos_config_id = fields.Many2one(
        "pos.config",
        string="Punto de venta heredado",
        index=True,
        ondelete="set null",
        check_company=False,
    )

    can_request = fields.Boolean(string="Solicitar")
    can_approve = fields.Boolean(string="Aprobar / rechazar")
    can_dispatch = fields.Boolean(string="Preparar / despachar")
    can_receive = fields.Boolean(string="Recibir / cerrar")

    def _effective_pos_configs(self):
        self.ensure_one()
        return self.pos_config_ids | self.pos_config_id

    def _warehouses_from_pos_configs(self, pos_configs):
        warehouses = self.env["stock.warehouse"]
        for pos_config in pos_configs:
            warehouses |= pos_config._ferreteria_transfer_warehouse()
        return warehouses

    def _effective_warehouses(self):
        self.ensure_one()
        pos_warehouses = self._warehouses_from_pos_configs(
            self._effective_pos_configs()
        )
        return self.warehouse_ids | self.warehouse_id | pos_warehouses

    def _normalize_scope(self):
        """Compatibility hook; POS branches are now derived, not copied.

        The warehouses selected explicitly by the administrator remain exactly
        as entered.  Warehouses implied by a POS are resolved dynamically from
        the POS Operation Type, preventing a stale ``pos.config.warehouse_id``
        from adding the company's default warehouse to the visible tags.
        """
        return True

    @api.constrains(
        "active",
        "user_id",
        "warehouse_ids",
        "pos_config_ids",
        "warehouse_id",
        "pos_config_id",
        "can_request",
        "can_approve",
        "can_dispatch",
        "can_receive",
    )
    def _check_permission_configuration(self):
        for permission in self:
            if permission.active and not permission._effective_warehouses():
                raise ValidationError(
                    _(
                        "Debe seleccionar al menos una sucursal/almacén o un punto de venta."
                    )
                )
            if permission.active and not any(
                (
                    permission.can_request,
                    permission.can_approve,
                    permission.can_dispatch,
                    permission.can_receive,
                )
            ):
                raise ValidationError(
                    _("Debe activar al menos un permiso o archivar la configuración.")
                )

    @api.model
    def _ensure_permission_admin(self):
        if not (self.env.su or self.env.user.has_group("base.group_system")):
            raise AccessError(
                _("Solo un administrador de Odoo puede configurar estos permisos.")
            )

    @api.model_create_multi
    def create(self, vals_list):
        self._ensure_permission_admin()
        permissions = super().create(vals_list)
        permissions._normalize_scope()
        permissions.mapped("user_id")._sync_ferreteria_transfer_role_groups()
        return permissions

    def write(self, vals):
        self._ensure_permission_admin()
        users_before = self.mapped("user_id")
        result = super().write(vals)
        self._normalize_scope()
        (users_before | self.mapped("user_id"))._sync_ferreteria_transfer_role_groups()
        return result

    def unlink(self):
        self._ensure_permission_admin()
        users = self.mapped("user_id")
        result = super().unlink()
        users._sync_ferreteria_transfer_role_groups()
        return result
