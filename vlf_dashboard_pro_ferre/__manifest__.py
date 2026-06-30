# -*- coding: utf-8 -*-
{
    'name': 'Tecnodyne Dashboard Pro',
    'summary': 'Constructor de dashboards operativos con múltiples gráficas, filtros, exportación e importación para Odoo 18',
    'description': '''
Tecnodyne Dashboard Pro
=====================

Módulo original para Odoo 18. Crea un dashboard operativo tipo BI dentro de Odoo,
con constructor de dashboards, múltiples tipos de visualización, filtros avanzados, filtros personalizados,
auto-refresco, exportación, importación, drag and drop y dashboards predefinidos.

No incluye funciones de IA. La IA queda preparada como una mejora posterior.
No copia ni reutiliza código de módulos comerciales de terceros.
    ''',
    'version': '18.0.2.3.0',
    'category': 'Productivity/Reporting',
    'author': 'Tecnodyne / ChatGPT',
    'website': '',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'mail',
        'sale_management',
        'point_of_sale',
        'stock',
        'account',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/dashboard_views.xml',
        'views/dashboard_item_views.xml',
        'views/dataset_views.xml',
        'views/todo_views.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'vlf_dashboard_pro_ferre/static/src/css/dashboard.css',
            'vlf_dashboard_pro_ferre/static/src/js/dashboard_client.js',
            'vlf_dashboard_pro_ferre/static/src/xml/dashboard_templates.xml',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True,
    'auto_install': False,
}
