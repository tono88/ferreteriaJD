# -*- coding: utf-8 -*-

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Copy 18.0.2.2.0 single-branch fields into the new multi-select fields."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    Permission = env["ferreteria.transfer.user.permission"].sudo()

    for permission in Permission.search([]):
        warehouses = permission.warehouse_ids
        pos_configs = permission.pos_config_ids
        if permission.warehouse_id:
            warehouses |= permission.warehouse_id
        if permission.pos_config_id:
            pos_configs |= permission.pos_config_id
            warehouses |= permission.pos_config_id.warehouse_id
        values = {}
        if warehouses != permission.warehouse_ids:
            values["warehouse_ids"] = [(6, 0, warehouses.ids)]
        if pos_configs != permission.pos_config_ids:
            values["pos_config_ids"] = [(6, 0, pos_configs.ids)]
        if values:
            permission.with_context(
                ferreteria_skip_permission_scope_normalize=True
            ).write(values)

    env["res.users"].search([])._sync_ferreteria_transfer_role_groups()
