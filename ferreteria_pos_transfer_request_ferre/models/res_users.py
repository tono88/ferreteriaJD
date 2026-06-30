# -*- coding: utf-8 -*-

from odoo import _, Command, api, fields, models
from odoo.exceptions import AccessError


class ResUsers(models.Model):
    _inherit = "res.users"

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + [
            "ferreteria_transfer_warehouse_ids",
            "ferreteria_request_pos_ids",
            "ferreteria_request_warehouse_ids",
            "ferreteria_request_general_warehouse_ids",
            "ferreteria_approve_warehouse_ids",
            "ferreteria_dispatch_warehouse_ids",
            "ferreteria_receive_warehouse_ids",
        ]

    # Campo heredado de 18.0.2.1.0. Se conserva para migrar y mantener
    # compatibilidad, pero ya no gobierna la seguridad del flujo.
    ferreteria_transfer_warehouse_ids = fields.Many2many(
        "stock.warehouse",
        "ferreteria_transfer_user_warehouse_rel",
        "user_id",
        "warehouse_id",
        string="Almacenes autorizados (legado)",
        help="Campo anterior conservado únicamente para compatibilidad y migración.",
        check_company=True,
    )

    ferreteria_transfer_permission_ids = fields.One2many(
        "ferreteria.transfer.user.permission",
        "user_id",
        string="Permisos por usuario y sucursal",
    )
    ferreteria_request_pos_ids = fields.Many2many(
        "pos.config",
        "ferreteria_transfer_user_request_pos_rel",
        "user_id",
        "pos_config_id",
        string="POS donde puede solicitar",
        compute="_compute_ferreteria_transfer_scopes",
        store=True,
        compute_sudo=True,
    )
    ferreteria_request_warehouse_ids = fields.Many2many(
        "stock.warehouse",
        "ferreteria_transfer_user_request_wh_rel",
        "user_id",
        "warehouse_id",
        string="Sucursales incluidas en permisos de solicitud",
        compute="_compute_ferreteria_transfer_scopes",
        store=True,
        compute_sudo=True,
    )
    ferreteria_request_general_warehouse_ids = fields.Many2many(
        "stock.warehouse",
        "ferreteria_transfer_user_request_general_wh_rel",
        "user_id",
        "warehouse_id",
        string="Sucursales con solicitud para todos sus POS",
        compute="_compute_ferreteria_transfer_scopes",
        store=True,
        compute_sudo=True,
    )
    ferreteria_approve_warehouse_ids = fields.Many2many(
        "stock.warehouse",
        "ferreteria_transfer_user_approve_wh_rel",
        "user_id",
        "warehouse_id",
        string="Sucursales donde puede aprobar",
        compute="_compute_ferreteria_transfer_scopes",
        store=True,
        compute_sudo=True,
    )
    ferreteria_dispatch_warehouse_ids = fields.Many2many(
        "stock.warehouse",
        "ferreteria_transfer_user_dispatch_wh_rel",
        "user_id",
        "warehouse_id",
        string="Sucursales donde puede despachar",
        compute="_compute_ferreteria_transfer_scopes",
        store=True,
        compute_sudo=True,
    )
    ferreteria_receive_warehouse_ids = fields.Many2many(
        "stock.warehouse",
        "ferreteria_transfer_user_receive_wh_rel",
        "user_id",
        "warehouse_id",
        string="Sucursales donde puede recibir",
        compute="_compute_ferreteria_transfer_scopes",
        store=True,
        compute_sudo=True,
    )

    @api.depends(
        "ferreteria_transfer_permission_ids.active",
        "ferreteria_transfer_permission_ids.warehouse_ids",
        "ferreteria_transfer_permission_ids.pos_config_ids",
        "ferreteria_transfer_permission_ids.warehouse_id",
        "ferreteria_transfer_permission_ids.pos_config_id",
        "ferreteria_transfer_permission_ids.can_request",
        "ferreteria_transfer_permission_ids.can_approve",
        "ferreteria_transfer_permission_ids.can_dispatch",
        "ferreteria_transfer_permission_ids.can_receive",
    )
    def _compute_ferreteria_transfer_scopes(self):
        Warehouse = self.env["stock.warehouse"]
        PosConfig = self.env["pos.config"]
        for user in self:
            permissions = user.ferreteria_transfer_permission_ids.filtered("active")
            request_pos = PosConfig
            request_warehouses = Warehouse
            request_general_warehouses = Warehouse
            approve_warehouses = Warehouse
            dispatch_warehouses = Warehouse
            receive_warehouses = Warehouse

            for permission in permissions:
                warehouses = permission._effective_warehouses()
                pos_configs = permission._effective_pos_configs()
                if permission.can_request:
                    request_pos |= pos_configs
                    request_warehouses |= warehouses
                    if not pos_configs:
                        request_general_warehouses |= warehouses
                if permission.can_approve:
                    approve_warehouses |= warehouses
                if permission.can_dispatch:
                    dispatch_warehouses |= warehouses
                if permission.can_receive:
                    receive_warehouses |= warehouses

            user.ferreteria_request_pos_ids = request_pos
            user.ferreteria_request_warehouse_ids = request_warehouses
            user.ferreteria_request_general_warehouse_ids = request_general_warehouses
            user.ferreteria_approve_warehouse_ids = approve_warehouses
            user.ferreteria_dispatch_warehouse_ids = dispatch_warehouses
            user.ferreteria_receive_warehouse_ids = receive_warehouses

    def _sync_ferreteria_transfer_role_groups(self):
        """Keep technical groups aligned with the permission matrix."""
        if not self:
            return
        group_map = {
            "can_request": self.env.ref(
                "ferreteria_pos_transfer_request_ferre.group_transfer_requester"
            ),
            "can_approve": self.env.ref(
                "ferreteria_pos_transfer_request_ferre.group_transfer_approver"
            ),
            "can_dispatch": self.env.ref(
                "ferreteria_pos_transfer_request_ferre.group_transfer_dispatcher"
            ),
            "can_receive": self.env.ref(
                "ferreteria_pos_transfer_request_ferre.group_transfer_receiver"
            ),
        }
        admin_group = self.env.ref(
            "ferreteria_pos_transfer_request_ferre.group_transfer_request_admin"
        )
        for user in self.sudo():
            if admin_group in user.groups_id:
                continue
            active_permissions = user.ferreteria_transfer_permission_ids.filtered(
                "active"
            )
            commands = []
            for field_name, group in group_map.items():
                should_have = any(active_permissions.mapped(field_name))
                has_group = group in user.groups_id
                if should_have and not has_group:
                    commands.append(Command.link(group.id))
                elif not should_have and has_group:
                    commands.append(Command.unlink(group.id))
            if commands:
                user.with_context(
                    ferreteria_skip_role_sync=True
                ).write({"groups_id": commands})

    def _ferreteria_has_transfer_permission(
        self, role, warehouse=None, pos_config=None
    ):
        self.ensure_one()
        if self.has_group(
            "ferreteria_pos_transfer_request_ferre.group_transfer_request_admin"
        ):
            return True
        field_by_role = {
            "approve": "ferreteria_approve_warehouse_ids",
            "dispatch": "ferreteria_dispatch_warehouse_ids",
            "receive": "ferreteria_receive_warehouse_ids",
        }
        if role == "request":
            target_warehouse = (
                pos_config._ferreteria_transfer_warehouse()
                if pos_config
                else warehouse
            )
            if pos_config and pos_config in self.ferreteria_request_pos_ids:
                return True
            return bool(
                target_warehouse
                and target_warehouse in self.ferreteria_request_general_warehouse_ids
            )
        field_name = field_by_role.get(role)
        if not field_name:
            return False
        return bool(warehouse and warehouse in self[field_name])

    def write(self, vals):
        if "ferreteria_transfer_warehouse_ids" in vals:
            if not (self.env.su or self.env.user.has_group("base.group_system")):
                raise AccessError(
                    _("Solo un administrador puede cambiar los almacenes autorizados.")
                )
        result = super().write(vals)
        if (
            "groups_id" in vals
            and not self.env.context.get("ferreteria_skip_role_sync")
        ):
            # Si se retira el grupo administrador, se reconstruyen los grupos
            # técnicos a partir de la matriz de permisos.
            self._sync_ferreteria_transfer_role_groups()
        return result
