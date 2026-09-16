{
    "name": "Ferretería - Seguridad por POS y almacén",
    "version": "18.0.1.0.2",
    "summary": "Ámbito operativo reutilizable por usuario, POS y almacén",
    "category": "Administration/Access Rights",
    "author": "DISTRIBUIDORA Y FERRETERÍA JB",
    "license": "LGPL-3",
    "depends": [
        "point_of_sale",
        "sale_stock",
        "stock",
        "ferreteria_pos_transfer_request_ferre",
        "pos_order_manual_payment_ferre",
        "pos_order_master_payment_ferre",
    ],
    "data": [
        "security/security.xml",
        "views/res_users_views.xml",
    ],
    "installable": True,
    "application": False,
}
