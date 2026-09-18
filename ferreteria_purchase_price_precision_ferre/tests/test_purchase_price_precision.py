from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPurchasePricePrecision(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Use existing master data so project-specific automatic partner codes
        # are not exercised by this isolated precision test.
        cls.vendor = cls.env["res.partner"].search(
            [("supplier_rank", ">", 0)], limit=1
        )
        cls.product = cls.env["product.product"].search(
            [("purchase_ok", "=", True)], limit=1
        )
        if not cls.vendor or not cls.product:
            raise AssertionError("The test database needs one vendor and one purchasable product")

    def _new_order(self, price):
        return self.env["purchase.order"].create({
            "partner_id": self.vendor.id,
            "order_line": [(0, 0, {
                "product_id": self.product.id,
                "name": self.product.display_name,
                "product_qty": 1.0,
                "product_uom": self.product.uom_po_id.id,
                "price_unit": price,
            })],
        })

    def test_storage_reload_and_copy(self):
        values = (0.12345678, 1.00000001, 15.1234, 125.99999999)
        for value in values:
            order = self._new_order(value)
            self.assertAlmostEqual(order.order_line.price_unit, value, places=8)
            order.invalidate_recordset()
            self.assertAlmostEqual(order.order_line.price_unit, value, places=8)
            duplicate = order.copy()
            self.assertAlmostEqual(duplicate.order_line.price_unit, value, places=8)

    def test_supplier_price_storage(self):
        supplier_info = self.env["product.supplierinfo"].create({
            "partner_id": self.vendor.id,
            "product_tmpl_id": self.product.product_tmpl_id.id,
            "price": 0.12345678,
        })
        supplier_info.invalidate_recordset()
        self.assertAlmostEqual(supplier_info.price, 0.12345678, places=8)

    def test_display_contract(self):
        cases = {
            0: "0.00",
            1: "1.00",
            1.2: "1.20",
            1.234: "1.234",
            1.2345: "1.2345",
            1.23456789: "1.23456789",
        }
        for value, expected in cases.items():
            line = self._new_order(value).order_line
            rendered = line.with_context(lang="en_US").ferreteria_format_purchase_price()
            self.assertEqual(rendered, expected)

    def test_purchase_to_vendor_bill_preserves_price(self):
        value = 12.12345678
        order = self._new_order(value)
        order.button_confirm()
        order.order_line.qty_received = 1.0
        order.action_create_invoice()
        bill = order.invoice_ids
        bill_line = bill.invoice_line_ids.filtered(lambda line: line.purchase_line_id)
        self.assertEqual(len(bill_line), 1)
        self.assertAlmostEqual(bill_line.price_unit, value, places=8)
        bill_line.invalidate_recordset()
        self.assertAlmostEqual(bill_line.price_unit, value, places=8)

    def test_customer_invoice_keeps_standard_product_price_rounding(self):
        customer = self.env["res.partner"].search(
            [("customer_rank", ">", 0)], limit=1
        ) or self.vendor
        invoice = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": customer.id,
            "invoice_line_ids": [(0, 0, {
                "name": "F8 precision sales regression",
                "quantity": 1.0,
                "price_unit": 12.12345678,
            })],
        })
        invoice_line = invoice.invoice_line_ids.filtered(
            lambda line: line.display_type == "product"
        )
        self.assertEqual(invoice_line.price_unit, 12.12)

    def test_value_matrix_and_monetary_rounding(self):
        values = (
            10,
            10.5,
            10.12,
            10.123,
            10.1234,
            10.123456,
            10.12345678,
            0.00000001,
        )
        for value in values:
            order = self._new_order(value)
            line = order.order_line
            line.write({
                "product_qty": 3.0,
                "discount": 7.5,
                "taxes_id": [(5, 0, 0)],
            })
            line.invalidate_recordset()
            self.assertAlmostEqual(line.price_unit, value, places=8)
            # Monetary amounts continue at currency precision.
            self.assertEqual(
                line.price_subtotal,
                order.currency_id.round(value * 3.0 * 0.925),
            )

    def test_qweb_reports_use_dynamic_purchase_format(self):
        order = self._new_order(15.12340000)
        purchase_html, _ = self.env["ir.actions.report"]._render_qweb_html(
            "purchase.report_purchaseorder", [order.id]
        )
        self.assertIn(b"15.1234", purchase_html)

        order.button_confirm()
        order.order_line.qty_received = 1.0
        order.action_create_invoice()
        bill = order.invoice_ids
        invoice_html, _ = self.env["ir.actions.report"]._render_qweb_html(
            "account.report_invoice", [bill.id]
        )
        self.assertIn(b"15.1234", invoice_html)
