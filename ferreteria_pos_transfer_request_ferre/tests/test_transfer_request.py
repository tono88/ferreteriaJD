# -*- coding: utf-8 -*-

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import new_test_user, tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestFerreteriaTransferRequest(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(
                cls.env.context,
                mail_create_nolog=True,
                mail_create_nosubscribe=True,
                mail_notrack=True,
                tracking_disable=True,
                no_reset_password=True,
            )
        )
        cls.company = cls.env.company
        cls.requesting_warehouse = cls.env["stock.warehouse"].create(
            {
                "name": "Test sucursal solicitante",
                "code": "TSR",
                "company_id": cls.company.id,
            }
        )
        cls.supplying_warehouse = cls.env["stock.warehouse"].create(
            {
                "name": "Test sucursal suministradora",
                "code": "TSS",
                "company_id": cls.company.id,
            }
        )
        cls.other_warehouse = cls.env["stock.warehouse"].create(
            {
                "name": "Test sucursal no autorizada",
                "code": "TNA",
                "company_id": cls.company.id,
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Martillo de prueba POS único",
                "default_code": "POS-STORABLE-TEST-UNIQUE",
                "barcode": "7500000000001",
                "is_storable": True,
            }
        )
        cls.non_storable_product = cls.env["product.product"].create(
            {
                "name": "Servicio de prueba POS único",
                "default_code": "POS-SERVICE-TEST-UNIQUE",
                "is_storable": False,
            }
        )
        cls.env["stock.quant"]._update_available_quantity(
            cls.product,
            cls.supplying_warehouse.lot_stock_id,
            25.0,
        )

        cls.pos_config = cls.env["pos.config"].create(
            {
                "name": "POS solicitante de prueba",
                "picking_type_id": cls.requesting_warehouse.pos_type_id.id,
            }
        )
        cls.other_pos_same_warehouse = cls.env["pos.config"].create(
            {
                "name": "Segundo POS de la misma sucursal",
                "picking_type_id": cls.requesting_warehouse.pos_type_id.id,
            }
        )

        cls.requester = new_test_user(
            cls.env,
            login="transfer_requester_test",
            groups="point_of_sale.group_pos_user",
        )
        cls.approver = new_test_user(
            cls.env,
            login="transfer_approver_test",
        )
        cls.receiver = new_test_user(
            cls.env,
            login="transfer_receiver_test",
        )
        cls.unauthorized_approver = new_test_user(
            cls.env,
            login="transfer_unauthorized_approver_test",
        )
        cls.unauthorized_requester = new_test_user(
            cls.env,
            login="transfer_unauthorized_requester_test",
            groups="point_of_sale.group_pos_user",
        )

        Permission = cls.env["ferreteria.transfer.user.permission"]
        Permission.create(
            {
                "user_id": cls.requester.id,
                "warehouse_ids": [Command.set([cls.requesting_warehouse.id])],
                "pos_config_ids": [Command.set([cls.pos_config.id])],
                "can_request": True,
            }
        )
        Permission.create(
            {
                "user_id": cls.approver.id,
                "warehouse_ids": [Command.set([cls.supplying_warehouse.id])],
                "can_approve": True,
                "can_dispatch": True,
            }
        )
        Permission.create(
            {
                "user_id": cls.receiver.id,
                "warehouse_ids": [Command.set([cls.requesting_warehouse.id])],
                "can_receive": True,
            }
        )
        Permission.create(
            {
                "user_id": cls.unauthorized_approver.id,
                "warehouse_ids": [Command.set([cls.other_warehouse.id])],
                "can_approve": True,
            }
        )
        Permission.create(
            {
                "user_id": cls.unauthorized_requester.id,
                "warehouse_ids": [Command.set([cls.other_warehouse.id])],
                "can_request": True,
            }
        )

    def _create_request(self, qty=8.0):
        return self.env["ferreteria.transfer.request"].with_user(self.requester).create(
            {
                "requesting_pos_id": self.pos_config.id,
                "requesting_warehouse_id": self.requesting_warehouse.id,
                "supplying_warehouse_id": self.supplying_warehouse.id,
                "request_note": "Solicitud de prueba automatizada",
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_uom_id": self.product.uom_id.id,
                            "requested_qty": qty,
                        }
                    )
                ],
            }
        )

    def test_full_backend_flow(self):
        request = self._create_request(qty=6.0)
        request.with_user(self.requester).action_submit()
        request.with_user(self.approver).action_approve_all()

        self.assertEqual(request.state, "approved")
        self.assertTrue(request.dispatch_picking_id)
        self.assertTrue(request.receipt_picking_id)
        self.assertNotEqual(request.dispatch_picking_id.state, "done")
        self.assertNotEqual(request.receipt_picking_id.state, "done")
        self.assertEqual(request.line_ids.reserved_qty, 6.0)

        with self.assertRaises(UserError):
            request.dispatch_picking_id.with_user(self.approver).button_validate()
        with self.assertRaises(UserError):
            request.dispatch_picking_id.with_user(self.approver).write(
                {"ferreteria_transfer_request_id": False}
            )

        request.with_user(self.approver).action_dispatch()
        self.assertEqual(request.state, "dispatched")
        self.assertEqual(request.dispatch_picking_id.state, "done")
        self.assertEqual(request.line_ids.dispatched_qty, 6.0)

        request.with_user(self.receiver).action_receive()
        self.assertEqual(request.state, "received")
        self.assertEqual(request.receipt_picking_id.state, "done")
        self.assertEqual(request.line_ids.received_qty, 6.0)
        destination_qty = self.env["stock.quant"]._get_available_quantity(
            self.product,
            self.requesting_warehouse.lot_stock_id,
        )
        self.assertEqual(destination_qty, 6.0)

        request.with_user(self.receiver).action_close()
        self.assertEqual(request.state, "closed")

    def test_partial_approval_and_short_receipt(self):
        request = self._create_request(qty=8.0)
        request.with_user(self.requester).action_submit()
        request.line_ids.with_user(self.approver).approved_qty = 5.0
        request.with_user(self.approver).action_approve_partial()
        self.assertEqual(request.state, "partial")
        self.assertEqual(request.line_ids.reserved_qty, 5.0)

        request.with_user(self.approver).action_dispatch()
        request.line_ids.with_user(self.receiver).received_qty = 3.0
        request.with_user(self.receiver).action_receive()

        self.assertEqual(request.state, "incident")
        self.assertEqual(request.line_ids.dispatched_qty, 5.0)
        self.assertEqual(request.line_ids.received_qty, 3.0)
        self.assertEqual(len(request.incident_ids), 1)
        self.assertEqual(request.incident_ids.incident_qty, 2.0)
        self.assertEqual(request.incident_ids.incident_type, "shortage")

        incident = request.incident_ids.with_user(self.receiver)
        incident.resolution_note = "Diferencia investigada y documentada."
        incident.action_resolve()
        request.with_user(self.receiver).action_close()
        self.assertEqual(request.state, "closed")

    def test_unauthorized_warehouse_cannot_approve(self):
        request = self._create_request(qty=2.0)
        request.with_user(self.requester).action_submit()
        with self.assertRaises(AccessError):
            request.with_user(self.unauthorized_approver).action_approve_all()

    def test_requesting_warehouse_domain_and_default(self):
        Request = self.env["ferreteria.transfer.request"].with_user(self.requester)
        selectable = self.env["stock.warehouse"].search(
            Request._get_requesting_warehouse_domain()
        )
        self.assertEqual(selectable, self.requesting_warehouse)

        request = Request.create(
            {
                "requesting_pos_id": self.pos_config.id,
                "supplying_warehouse_id": self.supplying_warehouse.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_uom_id": self.product.uom_id.id,
                            "requested_qty": 1.0,
                        }
                    )
                ],
            }
        )
        self.assertEqual(request.requesting_warehouse_id, self.requesting_warehouse)

    def test_pos_initial_data_uses_pos_warehouse(self):
        data = (
            self.env["ferreteria.transfer.request"]
            .with_user(self.requester)
            .pos_get_request_ui_data(self.pos_config.id)
        )
        self.assertEqual(data["pos_config_id"], self.pos_config.id)
        self.assertEqual(
            data["requesting_warehouse_id"], self.requesting_warehouse.id
        )
        supplier_ids = {warehouse["id"] for warehouse in data["supplying_warehouses"]}
        self.assertIn(self.supplying_warehouse.id, supplier_ids)
        self.assertIn(self.other_warehouse.id, supplier_ids)
        self.assertNotIn(self.requesting_warehouse.id, supplier_ids)

    def test_request_permission_is_limited_to_configured_pos(self):
        Request = self.env["ferreteria.transfer.request"].with_user(self.requester)
        with self.assertRaises(AccessError):
            Request.pos_get_request_ui_data(self.other_pos_same_warehouse.id)

    def test_permission_lines_sync_technical_groups(self):
        self.assertIn(
            self.env.ref("ferreteria_pos_transfer_request_ferre.group_transfer_requester"),
            self.requester.groups_id,
        )
        self.assertIn(
            self.env.ref("ferreteria_pos_transfer_request_ferre.group_transfer_approver"),
            self.approver.groups_id,
        )
        self.assertIn(
            self.env.ref("ferreteria_pos_transfer_request_ferre.group_transfer_dispatcher"),
            self.approver.groups_id,
        )
        self.assertIn(
            self.env.ref("ferreteria_pos_transfer_request_ferre.group_transfer_receiver"),
            self.receiver.groups_id,
        )


    def test_permission_record_accepts_multiple_warehouses_and_pos(self):
        multi_user = new_test_user(
            self.env,
            login="transfer_multi_scope_test",
            groups="point_of_sale.group_pos_user",
        )
        permission = self.env["ferreteria.transfer.user.permission"].create(
            {
                "user_id": multi_user.id,
                "warehouse_ids": [
                    Command.set(
                        [self.requesting_warehouse.id, self.supplying_warehouse.id]
                    )
                ],
                "pos_config_ids": [
                    Command.set(
                        [self.pos_config.id, self.other_pos_same_warehouse.id]
                    )
                ],
                "can_request": True,
                "can_approve": True,
            }
        )
        self.assertEqual(
            permission.warehouse_ids,
            self.requesting_warehouse | self.supplying_warehouse,
        )
        self.assertEqual(
            permission.pos_config_ids,
            self.pos_config | self.other_pos_same_warehouse,
        )
        self.assertTrue(
            multi_user._ferreteria_has_transfer_permission(
                "request", pos_config=self.pos_config
            )
        )
        self.assertTrue(
            multi_user._ferreteria_has_transfer_permission(
                "request", pos_config=self.other_pos_same_warehouse
            )
        )
        self.assertTrue(
            multi_user._ferreteria_has_transfer_permission(
                "approve", warehouse=self.supplying_warehouse
            )
        )

    def test_pos_operation_type_is_authoritative_over_stale_warehouse_field(self):
        # Simulate a database where the stored POS warehouse kept the company's
        # default warehouse although the visible Operation Type belongs to the
        # requesting branch.
        self.pos_config.write({"warehouse_id": self.other_warehouse.id})
        self.assertEqual(self.pos_config.warehouse_id, self.other_warehouse)
        self.assertEqual(
            self.pos_config._ferreteria_transfer_warehouse(),
            self.requesting_warehouse,
        )

        scoped_user = new_test_user(
            self.env,
            login="transfer_operation_type_scope_test",
            groups="point_of_sale.group_pos_user",
        )
        permission = self.env["ferreteria.transfer.user.permission"].create(
            {
                "user_id": scoped_user.id,
                "pos_config_ids": [Command.set([self.pos_config.id])],
                "can_request": True,
            }
        )
        # Selecting a POS no longer mutates the explicit visible warehouse tags.
        self.assertFalse(permission.warehouse_ids)
        self.assertEqual(
            permission._effective_warehouses(), self.requesting_warehouse
        )
        self.assertTrue(
            scoped_user._ferreteria_has_transfer_permission(
                "request", pos_config=self.pos_config
            )
        )

        data = (
            self.env["ferreteria.transfer.request"]
            .with_user(scoped_user)
            .pos_get_request_ui_data(self.pos_config.id)
        )
        self.assertEqual(
            data["requesting_warehouse_id"], self.requesting_warehouse.id
        )

    def test_request_permission_without_pos_applies_to_all_branch_pos(self):
        general_user = new_test_user(
            self.env,
            login="transfer_general_branch_test",
            groups="point_of_sale.group_pos_user",
        )
        self.env["ferreteria.transfer.user.permission"].create(
            {
                "user_id": general_user.id,
                "warehouse_ids": [Command.set([self.requesting_warehouse.id])],
                "can_request": True,
            }
        )
        self.assertTrue(
            general_user._ferreteria_has_transfer_permission(
                "request", pos_config=self.pos_config
            )
        )
        self.assertTrue(
            general_user._ferreteria_has_transfer_permission(
                "request", pos_config=self.other_pos_same_warehouse
            )
        )

    def test_pos_product_search_only_returns_storable_products(self):
        result = (
            self.env["ferreteria.transfer.request"]
            .with_user(self.requester)
            .pos_search_request_products(
                self.pos_config.id,
                self.supplying_warehouse.id,
                "POS-",
                80,
            )
        )
        product_ids = {product["id"] for product in result["products"]}
        self.assertIn(self.product.id, product_ids)
        self.assertNotIn(self.non_storable_product.id, product_ids)
        product_payload = next(
            product for product in result["products"] if product["id"] == self.product.id
        )
        self.assertEqual(product_payload["available_qty"], 25.0)


    def test_pos_product_search_ranks_exact_internal_reference_and_barcode(self):
        Request = self.env["ferreteria.transfer.request"].with_user(self.requester)

        by_code = Request.pos_search_request_products(
            self.pos_config.id,
            self.supplying_warehouse.id,
            "POS-STORABLE-TEST-UNIQUE",
            30,
        )
        self.assertTrue(by_code["products"])
        self.assertEqual(by_code["products"][0]["id"], self.product.id)
        self.assertEqual(by_code["exact_match_id"], self.product.id)

        by_barcode = Request.pos_search_request_products(
            self.pos_config.id,
            self.supplying_warehouse.id,
            "7500000000001",
            30,
        )
        self.assertTrue(by_barcode["products"])
        self.assertEqual(by_barcode["products"][0]["id"], self.product.id)
        self.assertEqual(by_barcode["exact_match_id"], self.product.id)

        by_name = Request.pos_search_request_products(
            self.pos_config.id,
            self.supplying_warehouse.id,
            "Martillo de prueba",
            30,
        )
        self.assertIn(self.product.id, {item["id"] for item in by_name["products"]})

    def test_pos_create_request_submits_without_stock_movement(self):
        Request = self.env["ferreteria.transfer.request"].with_user(self.requester)
        result = Request.pos_create_request_from_ui(
            self.pos_config.id,
            {
                "supplying_warehouse_id": self.supplying_warehouse.id,
                "partner_id": False,
                "request_note": "Creada desde prueba de interfaz POS",
                "lines": [
                    {
                        "product_id": self.product.id,
                        "qty": 4.0,
                        "note": "Línea creada desde POS",
                    }
                ],
            },
        )
        request = self.env["ferreteria.transfer.request"].browse(
            result["request_id"]
        )
        self.assertEqual(request.state, "submitted")
        self.assertEqual(request.requester_id, self.requester)
        self.assertEqual(request.requesting_pos_id, self.pos_config)
        self.assertEqual(request.requesting_warehouse_id, self.requesting_warehouse)
        self.assertEqual(request.supplying_warehouse_id, self.supplying_warehouse)
        self.assertEqual(request.line_ids.product_id, self.product)
        self.assertEqual(request.line_ids.requested_qty, 4.0)
        self.assertFalse(request.dispatch_picking_id)
        self.assertFalse(request.receipt_picking_id)
        self.assertEqual(request.line_ids.reserved_qty, 0.0)
        self.assertEqual(result["state"], "submitted")

    def test_pos_create_rejects_non_storable_product(self):
        Request = self.env["ferreteria.transfer.request"].with_user(self.requester)
        with self.assertRaises(UserError):
            Request.pos_create_request_from_ui(
                self.pos_config.id,
                {
                    "supplying_warehouse_id": self.supplying_warehouse.id,
                    "lines": [
                        {
                            "product_id": self.non_storable_product.id,
                            "qty": 1.0,
                        }
                    ],
                },
            )

    def test_pos_requester_must_be_authorized_for_current_pos_warehouse(self):
        Request = self.env["ferreteria.transfer.request"].with_user(
            self.unauthorized_requester
        )
        with self.assertRaises(AccessError):
            Request.pos_get_request_ui_data(self.pos_config.id)
