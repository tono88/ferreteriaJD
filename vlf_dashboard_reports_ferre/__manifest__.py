# -*- coding: utf-8 -*-
{
    'name': 'Tecnodyne Dashboard Reports - Ferretería',
    'summary': 'Métricas consolidadas de Ventas y POS para Tecnodyne Dashboard Pro',
    'description': '''
Primera entrega de la capa gerencial para vlf_dashboard_pro_ferre.

Incluye:
- ventas operativas consolidadas sin duplicar facturas POS;
- separación entre Ventas administrativas y Punto de Venta;
- devoluciones POS y notas de crédito administrativas relacionadas con ventas;
- dimensión de sucursal basada en stock.warehouse;
- métricas oficiales y presets administrados;
- endurecimiento del motor genérico de fechas, acumulados, totales y stock interno.
    ''',
    'version': '18.0.1.0.4',
    'category': 'Productivity/Reporting',
    'author': 'Ferretería / Tecnodyne extension',
    'license': 'LGPL-3',
    'depends': [
        'vlf_dashboard_pro_ferre',
        'sale_management',
        'sale_stock',
        'point_of_sale',
        'account',
        'stock',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/sales_fact_views.xml',
        'views/dashboard_views.xml',
        'wizard/update_presets_wizard_views.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'vlf_dashboard_reports_ferre/static/src/xml/dashboard_templates.xml',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
}
