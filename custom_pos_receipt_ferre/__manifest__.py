# -*- coding: utf-8 -*-
{
    "name": "POS Custom Receipt",
    "version": "18.0.1.2",
    "license": "OPL-1",
    "category": "Sales/Point of Sale",
    "author": "Kanak Infosystems LLP.",
    "website": "https://www.kanakinfosystems.com",
    "summary": "Datos personalizados del cliente en el recibo POS.",
    "depends": ["base", "point_of_sale"],
    "assets": {
        "point_of_sale._assets_pos": [
            "custom_pos_receipt_ferre/static/src/js/models.js",
            "custom_pos_receipt_ferre/static/src/xml/pos.xml",
        ],
    },
    "images": ["static/description/banner.jpg"],
    "installable": True,
    "application": False,
}
