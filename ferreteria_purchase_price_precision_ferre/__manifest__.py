{
    "name": "Ferretería - Precisión de precios de compra",
    "version": "18.0.1.0.0",
    "summary": "Conserva y presenta hasta 8 decimales en precios unitarios de Compras",
    "category": "Purchases",
    "author": "DISTRIBUIDORA Y FERRETERÍA JB",
    "license": "LGPL-3",
    "depends": ["purchase"],
    "data": [
        "views/purchase_views.xml",
        "views/product_supplierinfo_views.xml",
        "views/account_move_views.xml",
        "report/purchase_order_templates.xml",
        "report/account_invoice_templates.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "ferreteria_purchase_price_precision_ferre/static/src/js/purchase_price_field.js",
        ],
    },
    "installable": True,
    "application": False,
}

