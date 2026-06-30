# -*- coding: utf-8 -*-

{
    "name": "Megaprint FEL - Prueba segura de credenciales",
    "summary": "Prueba aislada del token FEL de Megaprint en ambiente QA",
    "version": "18.0.1.0.0",
    "category": "Accounting/Localizations",
    "author": "Proyecto Odoo 18 Ferretería",
    "license": "LGPL-3",
    "depends": [
        "fel_megaprint_ferre",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/credentials_test_result_views.xml",
        "views/account_journal_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
