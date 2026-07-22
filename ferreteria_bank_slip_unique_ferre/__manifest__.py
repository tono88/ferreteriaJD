# -*- coding: utf-8 -*-
{
    "name": "Ferretería - Boleta bancaria única",
    "version": "18.0.1.0.0",
    "summary": "Impide reutilizar números de boleta bancaria entre pagos de la compañía.",
    "category": "Accounting/Payments",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": [
        "account",
        "base_accounting_kit_ferre",
        "pos_order_manual_payment_ferre",
        "pos_order_master_payment_ferre",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/account_payment_views.xml",
        "views/pos_payment_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}
