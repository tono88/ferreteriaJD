{
    "name": "Ferretería JD - Cotizaciones desde el POS",
    "version": "18.0.1.1.0",
    "category": "Punto de venta",
    "summary": "Cotizaciones con almacén POS correcto, cobro e invoice POS único enlazado.",
    "author": "Ferretería JD",
    "depends": ["point_of_sale", "pos_sale", "sale_management", "mail"],
    "data": [
        "views/res_config_settings.xml",
        "views/sale_order_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "ferreteria_pos_cotizaciones/static/src/app/control_buttons.xml",
            "ferreteria_pos_cotizaciones/static/src/app/control_buttons.js",
            "ferreteria_pos_cotizaciones/static/src/app/pos_store.js",
        ],
    },
    "license": "LGPL-3",
    "application": False,
    "installable": True,
    "auto_install": False,
}
