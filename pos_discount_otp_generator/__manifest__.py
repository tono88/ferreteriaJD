{
    "name": "POS - Generador de autorizaciones de descuento",
    "version": "18.0.1.0.0",
    "category": "Punto de venta",
    "summary": "Genera códigos de un solo uso para autorizar descuentos en el POS.",
    "author": "Ferretería JD",
    "depends": ["point_of_sale", "pos_hr", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/otp_wizard_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "AGPL-3",
}
