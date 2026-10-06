# -*- coding: utf-8 -*-

from odoo import api, SUPERUSER_ID


BRANCH_RECEIPT_DATA = {
    "Palinche": {
        "thermal_receipt_commercial_name": "DISTRIBUIDORA Y FERRETERIA JB, S.A. Palinche",
        "thermal_receipt_address": "Carretera al pacifico lote 2, fracción 3 zona 0, Palín Escuintla",
        "thermal_receipt_phone": False,
    },
    "Taxisco": {
        "thermal_receipt_commercial_name": "DISTRIBUIDORA Y FERRETERIA JB, S.A. II Taxisco",
        "thermal_receipt_address": "Carretera a Taxisco Km 60 colonia Santa Marta",
        "thermal_receipt_phone": "45194239",
    },
    "El Salto": {
        "thermal_receipt_commercial_name": "DISTRIBUIDORA Y FERRETERIA JB, S.A. III El Salto",
        "thermal_receipt_address": "Kilómetro 58.1 Carretera al salto Villa Pereira Cantón Voladores Local A Zona 0",
        "thermal_receipt_phone": False,
    },
    "Gomera": {
        "thermal_receipt_commercial_name": "DISTRIBUIDORA Y FERRETERIA JB, S.A. VII Gomera",
        "thermal_receipt_address": "4ta Avenida Zona 0 Colonia 1 De Mayo La Gomera",
        "thermal_receipt_phone": False,
    },
    "Puerto": {
        "thermal_receipt_commercial_name": "DISTRIBUIDORA Y FERRETERIA JB, S.A. VIII Puerto 8",
        "thermal_receipt_address": "Calle La Esso Lote 7 Barrio Manglar Zona 0, San José, Escuintla.",
        "thermal_receipt_phone": False,
    },
}


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for pos_name, values in BRANCH_RECEIPT_DATA.items():
        config = env["pos.config"].search([("name", "=", pos_name)], limit=2)
        if len(config) == 1:
            config.write(values)
