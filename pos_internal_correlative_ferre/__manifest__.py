{
    "name": "POS Internal Correlative",
    "summary": "Correlativo interno backend para pedidos POS y facturas vinculadas.",
    "version": "18.0.1.0.13",
    "category": "Point of Sale",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": ["point_of_sale", "account"],
    "data": [
        "data/ir_sequence.xml",
        "views/pos_order_views.xml",
        "views/account_move_views.xml",
        "views/pos_config_views.xml",
    ],
    "installable": True,
    "application": False,
}
