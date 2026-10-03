{
    "name": "Ferretería - Existencias y Rentabilidad",
    "version": "18.0.1.0.1",
    "summary": "Existencias, última compra, costo y rentabilidad por ubicación",
    "category": "Inventory/Reporting",
    "author": "DISTRIBUIDORA Y FERRETERÍA JB",
    "license": "LGPL-3",
    "depends": ["stock", "purchase_stock", "sale_management", "ferreteria_user_scope_ferre"],
    "data": [
        "security/ir.model.access.csv",
        "views/inventory_profitability_views.xml",
    ],
    "external_dependencies": {"python": ["xlsxwriter"]},
    "installable": True,
    "application": False,
}
