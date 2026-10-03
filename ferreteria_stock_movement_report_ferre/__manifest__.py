{
    "name": "Ferretería - Historial de movimientos XLSX",
    "version": "18.0.1.0.0",
    "summary": "Usuario, proveedor y exportación segura del historial de inventario",
    "category": "Inventory/Reporting",
    "author": "DISTRIBUIDORA Y FERRETERÍA JB",
    "license": "LGPL-3",
    "depends": ["stock", "purchase_stock", "ferreteria_user_scope_ferre"],
    "data": [
        "security/ir.model.access.csv",
        "views/stock_move_line_views.xml",
        "views/movement_history_export_views.xml",
    ],
    "external_dependencies": {"python": ["xlsxwriter"]},
    "installable": True,
    "application": False,
}
