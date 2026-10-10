import base64
import io
import zipfile

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestInventoryLocationReport(TransactionCase):
    def setUp(self):
        super().setUp()
        self.quant_model = self.env["stock.quant"]
        self.stock_location = self.env.ref("stock.stock_location_stock")
        self.product = self.env["product.product"].create(
            {
                "name": "Producto prueba reporte ubicacion",
                "default_code": "LOC-REPORT-TEST",
                "is_storable": True,
            }
        )
        self.quant = self.env["stock.quant"].create(
            {
                "product_id": self.product.id,
                "location_id": self.stock_location.id,
                "quantity": 1.25,
            }
        )

    def test_domain_and_separate_columns(self):
        domain = [("id", "=", self.quant.id)]
        lines = self.quant_model._location_report_lines(domain)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["code"], "LOC-REPORT-TEST")
        self.assertEqual(lines[0]["product"], "Producto prueba reporte ubicacion")
        self.assertNotIn("[LOC-REPORT-TEST]", lines[0]["product"])
        self.assertEqual(lines[0]["quantity"], 1.25)

    def test_no_filter_matches_search(self):
        self.assertEqual(
            len(self.quant_model._location_report_lines([])),
            self.quant_model.search_count([]),
        )

    def test_warehouse_filter(self):
        warehouse = self.stock_location.warehouse_id
        domain = [("warehouse_id", "=", warehouse.id)]
        lines = self.quant_model._location_report_lines(domain)
        self.assertEqual(len(lines), self.quant_model.search_count(domain))
        self.assertTrue(any(line["code"] == "LOC-REPORT-TEST" for line in lines))

    def test_location_filter(self):
        domain = [("location_id", "=", self.stock_location.id)]
        lines = self.quant_model._location_report_lines(domain)
        self.assertEqual(len(lines), self.quant_model.search_count(domain))
        self.assertTrue(all(line["location"] == self.stock_location.complete_name for line in lines))

    def test_product_search(self):
        domain = [("product_id", "=", self.product.id)]
        lines = self.quant_model._location_report_lines(domain)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["product"], self.product.name)

    def test_reference_search(self):
        domain = [("product_id.default_code", "=", "LOC-REPORT-TEST")]
        lines = self.quant_model._location_report_lines(domain)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["code"], "LOC-REPORT-TEST")

    def test_combined_filters(self):
        domain = [
            ("warehouse_id", "=", self.stock_location.warehouse_id.id),
            ("location_id", "=", self.stock_location.id),
            ("product_id", "=", self.product.id),
        ]
        self.assertEqual(len(self.quant_model._location_report_lines(domain)), 1)

    def test_decimal_quantity_is_numeric_and_clean(self):
        line = self.quant_model._location_report_lines([("id", "=", self.quant.id)])[0]
        self.assertIsInstance(line["quantity"], float)
        self.assertEqual(line["quantity_display"], "1.25")

    def test_xlsx_is_valid_and_numeric(self):
        action = self.quant_model.action_export_location_report_xlsx(
            [("id", "=", self.quant.id)], "Producto: prueba", "[('id', '=', 1)]"
        )
        download_id = int(action["url"].split("/")[4])
        download = self.env["ferreteria.inventory.location.report.download"].browse(download_id)
        binary = base64.b64decode(download.file_data)
        with zipfile.ZipFile(io.BytesIO(binary)) as archive:
            sheet_xml = archive.read("xl/worksheets/sheet1.xml").decode()
            self.assertIn("LOC-REPORT-TEST", archive.read("xl/sharedStrings.xml").decode())
            self.assertIn('<c r="D7" s="', sheet_xml)
            self.assertNotIn('<c r="D7" s="5" t="s">', sheet_xml)

    def test_pdf_action_keeps_domain_and_renders_long_table(self):
        quant_ids = [self.quant.id]
        for index in range(65):
            product = self.env["product.product"].create(
                {
                    "name": f"Producto multipagina {index:02d}",
                    "default_code": f"LOC-PAGE-{index:02d}",
                    "is_storable": True,
                }
            )
            quant_ids.append(
                self.env["stock.quant"].create(
                    {
                        "product_id": product.id,
                        "location_id": self.stock_location.id,
                        "quantity": index + 0.5,
                    }
                ).id
            )
        domain = [("id", "in", quant_ids)]
        action = self.quant_model.action_print_location_report(domain, "Productos de prueba")
        self.assertEqual(action["type"], "ir.actions.report")
        self.assertEqual(action["data"]["domain"], domain)
        html, _ = self.env["ir.actions.report"]._render_qweb_html(
            "ferreteria_inventory_location_report_ferre.action_inventory_location_pdf",
            docids=[],
            data=action["data"],
        )
        self.assertIn(b"Producto multipagina 64", html)
        self.assertIn(b"display: table-header-group", html)

    def test_current_user_record_rules_are_respected(self):
        restricted_location = self.env["stock.location"].create(
            {
                "name": "Ubicacion no autorizada prueba",
                "location_id": self.stock_location.location_id.id,
                "usage": "internal",
            }
        )
        restricted_product = self.env["product.product"].create(
            {
                "name": "Producto oculto prueba",
                "default_code": "LOC-HIDDEN-TEST",
                "is_storable": True,
            }
        )
        hidden_quant = self.env["stock.quant"].create(
            {
                "product_id": restricted_product.id,
                "location_id": restricted_location.id,
                "quantity": 2.0,
            }
        )
        user = self.env["res.users"].create(
            {
                "name": "Catherine equivalente reporte",
                "login": "catherine.report.test@invalid.local",
                "company_id": self.env.company.id,
                "company_ids": [(6, 0, self.env.company.ids)],
                "groups_id": [
                    (6, 0, [self.env.ref("stock.group_stock_user").id])
                ],
            }
        )
        self.env["ir.rule"].create(
            {
                "name": "Regla global temporal reporte ubicacion",
                "model_id": self.env["ir.model"]._get_id("stock.quant"),
                "domain_force": f"[('location_id', '=', {self.stock_location.id})]",
                "global": True,
                "perm_read": True,
                "perm_write": False,
                "perm_create": False,
                "perm_unlink": False,
            }
        )
        secured_model = self.quant_model.with_user(user)
        visible_ids = secured_model._location_report_quants([]).ids
        self.assertIn(self.quant.id, visible_ids)
        self.assertNotIn(hidden_quant.id, visible_ids)

    def test_both_location_views_use_custom_controller(self):
        for xml_id in ("stock.view_stock_quant_tree", "stock.view_stock_quant_tree_editable"):
            view = self.env.ref(xml_id)
            arch = self.quant_model.get_view(view_id=view.id, view_type="list")["arch"]
            self.assertIn('js_class="ferreteria_inventory_location_report_list"', arch)

