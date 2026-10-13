# -*- coding: utf-8 -*-

from unittest.mock import patch

from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
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
        self.assertEqual(request.receipt_picking_id.state, "done")
        self.assertFalse(
            self.env["stock.picking"].sudo().search(
                [("backorder_id", "=", request.receipt_picking_id.id)]
            )
        )
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
        self.assertEqual(request.state, "submitted")
        self.assertFalse(self.env["stock.picking"].sudo().search([
            ("ferreteria_transfer_request_id", "=", request.id),
        ]))

    def _simulate_requesting_pos_outside_approver_scope(self, observed):
        """Simulate the POS record rule from STS/2026/00038, independently
        of the host's installed ferreteria_user_scope_ferre version.

        Every lookup of the requesting POS is recorded.  The supplier's
        approver receives AccessError for the ordinary POS field read.
        """
        PosClass = type(self.env["pos.config"])
        original_lookup = PosClass._ferreteria_transfer_warehouse
        pos_id = self.pos_config.id
        approver_id = self.approver.id

        def protected_lookup(pos):
            if pos.id == pos_id:
                observed.append((pos.env.uid, pos.env.su))
                if pos.env.uid == approver_id and not pos.env.su:
                    raise AccessError("No tiene acceso 'leer' a POS Mayoreo simulado")
            return original_lookup(pos)

        return patch.object(PosClass, "_ferreteria_transfer_warehouse", protected_lookup)

    def test_sts_2026_00038_approve_all_with_requesting_pos_unreadable(self):
        """Mayoreo -> Taxisco: permitted supplier approves, POS remains blocked."""
        request = self._create_request(qty=4.0)
        request.with_user(self.requester).action_submit()
        reads = []
        with self._simulate_requesting_pos_outside_approver_scope(reads):
            # A direct lookup remains forbidden outside the approved workflow.
            with self.assertRaises(AccessError):
                self.pos_config.with_user(self.approver)._ferreteria_transfer_warehouse()
            reads.clear()
            request.with_user(self.approver).action_approve_all()

        self.assertEqual(request.state, "approved")
        self.assertEqual(request.approved_by_id, self.approver)
        self.assertTrue(reads)
        self.assertTrue(all(uid == self.approver.id and su for uid, su in reads))
        self.assertEqual(request.dispatch_picking_id.picking_type_id,
                         self.supplying_warehouse.int_type_id)
        self.assertEqual(request.receipt_picking_id.picking_type_id,
                         self.requesting_warehouse.int_type_id)
        self.assertEqual(request.dispatch_picking_id.location_dest_id,
                         request.transit_location_id)
        self.assertEqual(request.receipt_picking_id.location_id,
                         request.transit_location_id)
        self.assertEqual(request.line_ids.dispatch_move_id.product_uom_qty, 4.0)
        self.assertEqual(request.line_ids.receipt_move_id.product_uom_qty, 4.0)

    def test_sts_2026_00038_partial_with_requesting_pos_unreadable(self):
        request = self._create_request(qty=8.0)
        request.with_user(self.requester).action_submit()
        request.line_ids.with_user(self.approver).approved_qty = 5.0
        reads = []
        with self._simulate_requesting_pos_outside_approver_scope(reads):
            request.with_user(self.approver).action_approve_partial()

        self.assertEqual(request.state, "partial")
        self.assertEqual(request.line_ids.approved_qty, 5.0)
        self.assertEqual(request.line_ids.dispatch_move_id.product_uom_qty, 5.0)
        self.assertEqual(request.line_ids.receipt_move_id.product_uom_qty, 5.0)
        self.assertTrue(reads)
        self.assertTrue(all(uid == self.approver.id and su for uid, su in reads))

    def test_sts_2026_00038_unauthorized_user_never_gets_pos_sudo(self):
        request = self._create_request(qty=2.0)
        request.with_user(self.requester).action_submit()
        reads = []
        with self._simulate_requesting_pos_outside_approver_scope(reads):
            with self.assertRaises(AccessError):
                request.with_user(self.unauthorized_approver).action_approve_all()
        self.assertEqual(reads, [])
        self.assertEqual(request.state, "submitted")
        self.assertFalse(self.env["stock.picking"].sudo().search([
            ("ferreteria_transfer_request_id", "=", request.id),
        ]))

    def test_sts_2026_00038_constraint_remains_without_sudo(self):
        """Create/edit constraint must not silently bypass requesting POS rules."""
        request = self._create_request(qty=2.0)
        request.with_user(self.requester).action_submit()
        reads = []
        with self._simulate_requesting_pos_outside_approver_scope(reads):
            with self.assertRaises(AccessError):
                request.with_user(self.approver)._check_branch_configuration()
        self.assertEqual(reads, [(self.approver.id, False)])

    def test_sts_2026_00038_technical_pos_read_still_validates_warehouse(self):
        """Sudo is only for reading; inconsistent warehouse must be rejected."""
        request = self._create_request(qty=2.0)
        request.with_user(self.requester).action_submit()
        PosClass = type(self.env["pos.config"])
        original_lookup = PosClass._ferreteria_transfer_warehouse

        def wrong_warehouse(pos):
            if pos.id == self.pos_config.id and pos.env.su:
                return self.other_warehouse
            return original_lookup(pos)

        with patch.object(PosClass, "_ferreteria_transfer_warehouse", wrong_warehouse):
            with self.assertRaises(ValidationError):
                request.with_user(self.approver).action_approve_all()
        request.invalidate_recordset()
        self.assertEqual(request.state, "submitted")
        self.assertFalse(self.env["stock.picking"].sudo().search([
            ("ferreteria_transfer_request_id", "=", request.id),
        ]))

    def test_receipt_creation_is_sudo_only_after_real_user_authorization(self):
        """Sudo solo en el picking remoto; despacho y validación no son sudo."""
        request = self._create_request(qty=3.0)
        request.with_user(self.requester).action_submit()
        PickingClass = type(self.env["stock.picking"])
        original_create = PickingClass.create
        observed = {}

        def audit_create(model, vals_list):
            values = vals_list[0] if isinstance(vals_list, list) else vals_list
            if values.get("ferreteria_transfer_request_id") == request.id:
                observed[values["ferreteria_transfer_stage"]] = (
                    model.env.su,
                    model.env.uid,
                )
            return original_create(model, vals_list)

        with patch.object(PickingClass, "create", audit_create):
            request.with_user(self.approver).action_approve_all()

        self.assertEqual(observed["dispatch"], (False, self.approver.id))
        self.assertEqual(observed["receipt"][0], True)
        self.assertEqual(request.approved_by_id, self.approver)
        self.assertEqual(request.dispatch_picking_id.picking_type_id,
                         self.supplying_warehouse.int_type_id)
        self.assertEqual(request.receipt_picking_id.picking_type_id,
                         self.requesting_warehouse.int_type_id)
        self.assertEqual(request.dispatch_picking_id.location_dest_id,
                         request.transit_location_id)
        self.assertEqual(request.receipt_picking_id.location_id,
                         request.transit_location_id)
        self.assertEqual(request.line_ids.dispatch_move_id.product_uom_qty, 3.0)
        self.assertEqual(request.line_ids.receipt_move_id.product_uom_qty, 3.0)
        self.assertIn(request.line_ids.dispatch_move_id,
                      request.line_ids.receipt_move_id.move_orig_ids)

    def test_failed_receipt_rolls_back_dispatch_and_approval(self):
        """Error después de crear despacho no deja pickings, moves ni estado."""
        request = self._create_request(qty=3.0)
        request.with_user(self.requester).action_submit()
        RequestClass = type(self.env["ferreteria.transfer.request"])
        original_prepare = RequestClass._prepare_picking_values

        def fail_receipt(record, stage):
            if stage == "receipt":
                raise UserError("Fallo simulado del segundo picking")
            return original_prepare(record, stage)

        with patch.object(RequestClass, "_prepare_picking_values", fail_receipt):
            with self.assertRaisesRegex(UserError, "Fallo simulado"):
                request.with_user(self.approver).action_approve_all()

        request.invalidate_recordset()
        request.line_ids.invalidate_recordset()
        self.assertEqual(request.state, "submitted")
        self.assertFalse(request.dispatch_picking_id)
        self.assertFalse(request.receipt_picking_id)
        self.assertFalse(request.approved_by_id)
        self.assertEqual(request.line_ids.approved_qty, 0.0)
        self.assertFalse(self.env["stock.picking"].sudo().search([
            ("ferreteria_transfer_request_id", "=", request.id),
        ]))
        self.assertFalse(self.env["stock.move"].sudo().search([
            ("origin", "=", request.name),
        ]))

    def test_failure_after_reservation_rolls_back_reserved_quants(self):
        """Si falla la reserva después de asignar stock, se revierte todo."""
        request = self._create_request(qty=3.0)
        request.with_user(self.requester).action_submit()
        Quant = self.env["stock.quant"].sudo()
        quant_domain = [
            ("product_id", "=", self.product.id),
            ("location_id", "=", self.supplying_warehouse.lot_stock_id.id),
        ]
        original_reserved = sum(Quant.search(quant_domain).mapped("reserved_quantity"))
        MoveClass = type(self.env["stock.move"])
        original_assign = MoveClass._action_assign

        def fail_after_assignment(moves, *args, **kwargs):
            result = original_assign(moves, *args, **kwargs)
            if any(move.picking_id.ferreteria_transfer_stage == "dispatch"
                   and move.picking_id.ferreteria_transfer_request_id.id == request.id
                   for move in moves):
                raise UserError("Fallo simulado después de la reserva")
            return result

        with patch.object(MoveClass, "_action_assign", fail_after_assignment):
            with self.assertRaisesRegex(UserError, "Fallo simulado"):
                request.with_user(self.approver).action_approve_all()

        request.invalidate_recordset()
        self.assertEqual(request.state, "submitted")
        self.assertFalse(self.env["stock.picking"].sudo().search([
            ("ferreteria_transfer_request_id", "=", request.id),
        ]))
        self.assertFalse(self.env["stock.move"].sudo().search([
            ("origin", "=", request.name),
        ]))
        self.assertEqual(
            sum(Quant.search(quant_domain).mapped("reserved_quantity")),
            original_reserved,
        )

    def test_reject_pending_request_without_stock_documents(self):
        request = self._create_request(qty=2.0)
        request.with_user(self.requester).action_submit()
        request.with_user(self.approver).write({
            "rejection_reason": "No hay disponibilidad para la solicitud.",
        })
        request.with_user(self.approver).action_reject()
        self.assertEqual(request.state, "rejected")
        self.assertFalse(self.env["stock.picking"].sudo().search([
            ("ferreteria_transfer_request_id", "=", request.id),
        ]))

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
