# -*- coding: utf-8 -*-
{
    "name": "Ferretería - Alertas de reabastecimiento por correo",
    "version": "18.0.1.0.0",
    "summary": "Envía una sola alerta por correo cuando una regla de reabastecimiento cae por debajo de su mínimo",
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
