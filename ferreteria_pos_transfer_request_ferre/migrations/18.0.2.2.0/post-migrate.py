# -*- coding: utf-8 -*-

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Convert the legacy shared warehouse list into role-specific permissions."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    cr.execute("SELECT to_regclass('ferreteria_transfer_user_warehouse_rel')")
    if not cr.fetchone()[0]:
        return

    cr.execute(
        """
        SELECT user_id, warehouse_id
          FROM ferreteria_transfer_user_warehouse_rel
         ORDER BY user_id, warehouse_id
        """
    )
    legacy_rows = cr.fetchall()
    Permission = env["ferreteria.transfer.user.permission"]
    requester_group = env.ref(
        "ferreteria_pos_transfer_request_ferre.group_transfer_requester"
    )
    approver_group = env.ref(
        "ferreteria_pos_transfer_request_ferre.group_transfer_approver"
    )
    receiver_group = env.ref(
        "ferreteria_pos_transfer_request_ferre.group_transfer_receiver"
    )

    for user_id, warehouse_id in legacy_rows:
        user = env["res.users"].browse(user_id).exists()
        warehouse = env["stock.warehouse"].browse(warehouse_id).exists()
        if not user or not warehouse:
            continue

        flags = {
            "can_request": requester_group in user.groups_id,
            "can_approve": approver_group in user.groups_id,
            # En la versión anterior el aprobador también preparaba y despachaba.
            "can_dispatch": approver_group in user.groups_id,
            "can_receive": receiver_group in user.groups_id,
        }
        if not any(flags.values()):
            continue

        domain = [
            ("user_id", "=", user.id),
            ("warehouse_id", "=", warehouse.id),
            ("pos_config_id", "=", False),
        ]
        permission = Permission.search(domain, limit=1)
        values = {
            "user_id": user.id,
            "warehouse_id": warehouse.id,
            "pos_config_id": False,
            **flags,
        }
        if permission:
            permission.write(
                {
                    key: bool(permission[key] or value)
                    for key, value in flags.items()
                }
            )
        else:
            Permission.create(values)

    env["res.users"].search([])._sync_ferreteria_transfer_role_groups()
