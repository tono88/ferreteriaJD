{
    "name": "Ferretería JD - Cajero único por usuario de Odoo",
    "version": "18.0.1.0.0",
    "category": "Punto de venta",
    "summary": "Sin PIN ni cambio de cajero; cierre de caja básico con reglas de Odoo.",
    "author": "Ferretería JD",
    "license": "LGPL-3",
    "depends": ["pos_discount_manager", "point_of_sale", "pos_hr"],
    "data": ["views/res_config_settings_views.xml"],
    "assets": {
        "point_of_sale._assets_pos": [
            "ferreteria_pos_cajero_unico_ferre/static/src/js/pos_store.js",
        ],
    },
    "installable": True,
    "application": False,
}
