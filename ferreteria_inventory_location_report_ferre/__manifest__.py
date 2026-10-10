{
    "name": "Ferreteria - Inventario por ubicacion PDF/XLSX",
    "summary": "Imprime y exporta el dominio activo del reporte de ubicaciones",
    "version": "18.0.1.0.0",
    "category": "Inventory/Inventory",
    "license": "LGPL-3",
    "author": "Custom",
    "depends": ["stock", "web"],
    "data": [
        "security/ir.model.access.csv",
        "report/inventory_location_report.xml",
        "views/stock_quant_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "ferreteria_inventory_location_report_ferre/static/src/js/inventory_location_report_list.js",
            "ferreteria_inventory_location_report_ferre/static/src/xml/inventory_location_report_buttons.xml",
        ],
    },
    "installable": True,
    "application": False,
}

