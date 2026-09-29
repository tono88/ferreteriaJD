# -*- coding: utf-8 -*-
{
    "name": "Ferretería - Bloqueo de ventas sin inventario",
    "summary": "Impide ventas POS, pedidos y facturas directas sin origen de inventario válido.",
    "version": "18.0.1.1.0",
    "category": "Inventory/Inventory",
    "author": "Ferretería JB",
    "license": "LGPL-3",
    "depends": [
        "point_of_sale",
        "stock",
        "sale_stock",
        "account",
    ],
    "data": [],
    "assets": {
        "point_of_sale._assets_pos": [
            "ferreteria_no_negative_stock_ferre/static/src/js/pos_stock_guard.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
