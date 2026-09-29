# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from ..models.stock_guard import validate_stock_requirements


@tagged("at_install", "-post_install")
class TestFerreteriaStockGuard(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.location = cls.env["stock.location"].create(
            {
                "name": "F7 Stock Guard",
                "usage": "internal",
                "company_id": cls.env.company.id,
            }
        )
        cls.unit = cls.env.ref("uom.product_uom_unit")
        cls.product = cls.env["product.product"].create(
            {
                "name": "F7 Producto Entero",
                "is_storable": True,
                "uom_id": cls.unit.id,
                "uom_po_id": cls.unit.id,
            }
        )
        cls.env["stock.quant"]._update_available_quantity(
            cls.product,
            cls.location,
            10.0,
        )

    def _validate(self, quantity, product=None):
        return validate_stock_requirements(
            self.env,
            location=self.location,
            requirements=[(product or self.product, quantity)],
            warehouse_name="F7",
        )

    def _new_product(self, name, uom=None):
        selected_uom = uom or self.unit
        return self.env["product.product"].create(
            {
                "name": name,
                "is_storable": True,
                "uom_id": selected_uom.id,
                "uom_po_id": selected_uom.id,
            }
        )

    def test_available_quantity_boundaries(self):
        self.assertTrue(self._validate(1.0))
        self.assertTrue(self._validate(10.0))
        with self.assertRaises(UserError):
            self._validate(11.0)

    def test_zero_and_negative_stock_block(self):
        empty_product = self._new_product("F7 Sin stock")
        negative_product = self._new_product("F7 Negativo")
        self.env["stock.quant"]._update_available_quantity(
            negative_product,
            self.location,
            -1.0,
        )
        with self.assertRaises(UserError):
            self._validate(1.0, empty_product)
        with self.assertRaises(UserError):
            self._validate(1.0, negative_product)

    def test_reserved_quantity_is_not_available(self):
        self.env["stock.quant"]._update_reserved_quantity(
            self.product,
            self.location,
            4.0,
        )
        self.assertTrue(self._validate(6.0))
        with self.assertRaises(UserError):
            self._validate(6.01)

    def test_duplicate_lines_are_aggregated(self):
        with self.assertRaises(UserError):
            validate_stock_requirements(
                self.env,
                location=self.location,
                requirements=[(self.product, 6.0), (self.product, 5.0)],
                warehouse_name="F7",
            )

    def test_decimal_rounding_and_refund(self):
        decimal_uom = self.env["uom.uom"].create(
            {
                "name": "F7 Decimal 0.01",
                "category_id": self.unit.category_id.id,
                "uom_type": "smaller",
                "factor_inv": 0.01,
                "rounding": 0.01,
            }
        )
        decimal_product = self._new_product("F7 Producto Decimal", decimal_uom)
        self.env["stock.quant"]._update_available_quantity(
            decimal_product,
            self.location,
            2.50,
        )
        self.assertTrue(self._validate(2.25, decimal_product))
        with self.assertRaises(UserError):
            self._validate(2.51, decimal_product)
        self.assertTrue(self._validate(-1.0, decimal_product))
