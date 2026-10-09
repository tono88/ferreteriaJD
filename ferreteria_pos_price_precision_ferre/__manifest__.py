# -*- coding: utf-8 -*-
{
    "name": "Ferretería - Precisión visual de precios POS",
    "version": "18.0.1.0.2",
    "category": "Point of Sale",
    "summary": "Muestra cantidad, precio unitario y total de línea con hasta 6 decimales en el POS",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": ["point_of_sale"],
    "data": [],
    "assets": {
        "point_of_sale.assets_prod": [
            "ferreteria_pos_price_precision_ferre/static/src/js/pos_order_line.js",
            "ferreteria_pos_price_precision_ferre/static/src/js/orderline.js",
            "ferreteria_pos_price_precision_ferre/static/src/xml/orderline.xml",
            "ferreteria_pos_price_precision_ferre/static/src/scss/orderline.scss",
        ],
        "point_of_sale.assets_debug": [
            "ferreteria_pos_price_precision_ferre/static/src/js/pos_order_line.js",
            "ferreteria_pos_price_precision_ferre/static/src/js/orderline.js",
            "ferreteria_pos_price_precision_ferre/static/src/xml/orderline.xml",
            "ferreteria_pos_price_precision_ferre/static/src/scss/orderline.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
