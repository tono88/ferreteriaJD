# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    ferreteria_pos_available_qty = fields.Float(
        string="Disponibilidad POS en sucursal",
        compute="_compute_ferreteria_pos_available_qty",
        digits="Product Unit of Measure",
        help=(
            "Cantidad disponible sin reservar en la ubicación principal del "
            "almacén del POS. Es una instantánea para advertencia inmediata; "
            "el servidor vuelve a validar al aceptar la orden."
        ),
    )

    @api.depends_context("ferreteria_pos_stock_location_id")
    def _compute_ferreteria_pos_available_qty(self):
        location_id = self.env.context.get("ferreteria_pos_stock_location_id")
        location = self.env["stock.location"].browse(location_id).exists()
        if not location:
            for product in self:
                product.ferreteria_pos_available_qty = 0.0
            return

        quant_model = self.env["stock.quant"].sudo()
        for product in self:
            product.ferreteria_pos_available_qty = quant_model._get_available_quantity(
                product,
                location,
                strict=False,
            )

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields_to_load = super()._load_pos_data_fields(config_id)
        if "ferreteria_pos_available_qty" not in fields_to_load:
            fields_to_load.append("ferreteria_pos_available_qty")
        return fields_to_load

    def _load_pos_data(self, data):
        config = self.env["pos.config"].browse(
            data["pos.config"]["data"][0]["id"]
        )
        warehouse = config.picking_type_id.warehouse_id
        location = warehouse.lot_stock_id if warehouse else self.env["stock.location"]
        product_with_location = self.with_context(
            ferreteria_pos_stock_location_id=location.id or False,
        )
        return super(ProductProduct, product_with_location)._load_pos_data(data)
