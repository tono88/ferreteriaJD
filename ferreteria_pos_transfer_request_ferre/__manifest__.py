# -*- coding: utf-8 -*-
{
    "name": "Ferretería - Solicitudes entre sucursales",
    "version": "18.0.2.3.1",
    "summary": "Solicitudes, aprobación, reserva, despacho y recepción entre sucursales",
    "category": "Inventory/Inventory",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": [
        "mail",
        "stock",
        "point_of_sale",
    ],
    "data": [
        "security/transfer_request_security.xml",
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "data/stock_location.xml",
        "views/res_users_views.xml",
        "views/transfer_user_permission_views.xml",
        "views/stock_picking_views.xml",
        "views/transfer_incident_views.xml",
        "views/transfer_request_views.xml",
        "views/menus.xml",
    ],
    "demo": [
        "demo/demo_data.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "ferreteria_pos_transfer_request_ferre/static/src/js/transfer_request_popup.js",
            "ferreteria_pos_transfer_request_ferre/static/src/js/transfer_request_button.js",
            "ferreteria_pos_transfer_request_ferre/static/src/xml/transfer_request_button.xml",
            "ferreteria_pos_transfer_request_ferre/static/src/xml/transfer_request_popup.xml",
            "ferreteria_pos_transfer_request_ferre/static/src/scss/transfer_request.scss",
        ],
    },
    "installable": True,
    "application": False,
}
