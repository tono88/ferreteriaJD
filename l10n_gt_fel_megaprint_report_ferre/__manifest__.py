{
    "name": "Guatemala FEL Megaprint - Reporte de Factura",
    "version": "18.0.1.0.1",
    "summary": "Formato de impresión FEL (Megaprint) para facturas",
    "author": "Tu Equipo",
    "license": "LGPL-3",
    "depends": ["account", "web", "point_of_sale", "stock", "sale_stock"],
    "data": [
        "reports/action_report.xml",
        "reports/report_fel_invoice.xml",
        'reports/external_layout_clean_footer.xml',
    ],
    "installable": True,
    "application": False,
}
