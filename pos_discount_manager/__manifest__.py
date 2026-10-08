{
    "name": "POS - Aprobación de descuentos por cajero",
    "version": "18.0.2.0.0",
    "category": "Punto de venta",
    "summary": "Límites de descuento individuales y autorización mediante códigos de un solo uso.",
    "description": "Los descuentos que superen el límite del cajero requieren aprobación. No se usa PIN fijo.",
    "author": "Cybrosys Technologies Pvt. Ltd.; adaptación Ferretería JD",
    "website": "https://www.cybrosys.com",
    "depends": ["pos_discount", "pos_hr", "pos_discount_otp_generator"],
    "data": ["views/hr_employee_views.xml"],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_discount_manager/static/src/js/payment_screen.js",
        ],
    },
    "license": "AGPL-3",
    "installable": True,
    "auto_install": False,
    "application": False,
}
