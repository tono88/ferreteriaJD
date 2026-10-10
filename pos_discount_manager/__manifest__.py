{
    "name": "POS - Aprobación de descuentos por cajero",
    "version": "18.0.2.2.0",
    "category": "Punto de venta",
    "summary": "Descuentos individuales/globales y autorizaciones OTP con empleado o cuenta de Odoo.",
    "description": "Soporta cajeros seleccionados por pos_hr o un único cajero vinculado a la cuenta autenticada de Odoo.",
    "author": "Cybrosys Technologies Pvt. Ltd.; adaptación Ferretería JD",
    "website": "https://www.cybrosys.com",
    "depends": ["pos_discount", "pos_hr", "pos_discount_otp_generator"],
    "data": ["views/hr_employee_views.xml"],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_discount_manager/static/src/js/discount_guard.js",
            "pos_discount_manager/static/src/js/payment_screen.js",
        ],
    },
    "license": "AGPL-3",
    "installable": True,
    "auto_install": False,
    "application": False,
}
