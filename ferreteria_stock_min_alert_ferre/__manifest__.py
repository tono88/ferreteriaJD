# -*- coding: utf-8 -*-
{
    "name": "Ferretería - Alertas de reabastecimiento por correo",
    "version": "18.0.1.0.2",
    "summary": "Envía automáticamente una sola alerta por correo cuando el inventario cae por debajo del mínimo",
    "category": "Inventory/Inventory",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": [
        "mail",
        "stock",
    ],
    "data": [
        "views/res_users_views.xml",
        "views/stock_warehouse_orderpoint_views.xml",
        "data/ir_cron.xml",
    ],
    "installable": True,
    "application": False,
}
