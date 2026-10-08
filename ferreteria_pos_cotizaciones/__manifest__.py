{
    "name": "Ferretería JD - Cotizaciones desde el POS",
    "version": "18.0.1.0.0",
    "category": "Punto de venta",
    "summary": "Crear, visualizar, enviar por correo, imprimir y gestionar cotizaciones desde el POS.",
    "author": "Ferretería JD",
    "depends": ["point_of_sale", "pos_sale", "sale_management", "mail"],
    "data": ["views/res_config_settings.xml"],
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
