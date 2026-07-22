# -*- coding: utf-8 -*-

{
    "name": "Ferretería - Ticket FEL para Punto de Venta",
    "version": "18.0.1.0.2",
    "category": "Point of Sale",
    "summary": "Recibo POS con datos FEL y ticket térmico PDF desde el backend",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": [
        "point_of_sale",
        "account",
        "pos_internal_correlative_ferre",
    ],
    "data": [
        "report/pos_fel_ticket_report.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "ferreteria_pos_fel_ticket/static/src/js/pos_order.js",
            "ferreteria_pos_fel_ticket/static/src/js/receipt_screen.js",
            "ferreteria_pos_fel_ticket/static/src/xml/order_receipt.xml",
            "ferreteria_pos_fel_ticket/static/src/scss/pos_fel_ticket.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
