from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestPaymentBatchBankSlip(AccountTestInvoicingCommon):
    def _invoice(self, partner):
        invoice = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": partner.id,
            "invoice_date": "2026-10-01",
            # partner_b in the accounting fixture has installment terms; this
            # suite tests full bank-slip payments, not the due-installment UI.
            "invoice_payment_term_id": False,
            "invoice_line_ids": [Command.create({
                "name": "Bank slip regression",
                "account_id": self.company_data["default_account_revenue"].id,
                "quantity": 1,
                "price_unit": 100,
                "tax_ids": [Command.clear()],
            })],
        })
        invoice.action_post()
        return invoice

    def _wizard(self, invoices, number):
        return self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=invoices.ids,
        ).create({
            "journal_id": self.company_data["default_journal_bank"].id,
            "bank_reference": number,
            "group_payment": False,
        })

    def test_register_multiple_customers_one_slip(self):
        invoices = self._invoice(self.partner_a) | self._invoice(self.partner_b)
        payments = self._wizard(invoices, "04776092910")._create_payments()
        self.assertEqual(len(payments), 2)
        self.assertEqual(set(payments.mapped("bank_reference")), {"04776092910"})
        registry = self.env["ferreteria.bank.slip.registry"].sudo()
        claim = registry.search([("number_normalized", "=", "04776092910")])
        self.assertEqual(len(claim), 1)
        self.assertEqual(claim.payment_ids, payments)
        # Subsequent writes on either member must still work.
        for payment in payments:
            payment.write({"bank_reference": " 04776092910 "})
        # A second wizard cannot reuse the number. Its whole operation rolls back.
        other = self._invoice(self.partner_a)
        before = self.env["account.payment"].search_count([])
        with self.assertRaises(ValidationError):
            self._wizard(other, "04776092910")._create_payments()
        self.assertEqual(self.env["account.payment"].search_count([]), before)

    def test_no_reference_and_distinct_operations(self):
        invoices = self._invoice(self.partner_a) | self._invoice(self.partner_b)
        payments = self._wizard(invoices, False)._create_payments()
        self.assertEqual(len(payments), 2)
        self.assertFalse(payments.mapped("bank_reference")[0])
        first = self._wizard(self._invoice(self.partner_a), "BANK-A")._create_payments()
        second = self._wizard(self._invoice(self.partner_b), "BANK-B")._create_payments()
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            second.write({"bank_reference": first.bank_reference})

    def test_rpc_context_cannot_disable_claim(self):
        first = self._wizard(self._invoice(self.partner_a), "RPC-123")._create_payments()
        for marker in (True, "True", [], {}):
            with self.assertRaises(ValidationError), self.env.cr.savepoint():
                first.with_context(_bank_slip_register_batch=marker).copy({
                    "bank_reference": "rpc-123",
                })

    def test_history_keeps_number_after_edit(self):
        first = self._wizard(self._invoice(self.partner_a), "OLD-SLIP")._create_payments()
        first.write({"bank_reference": "NEW-SLIP"})
        with self.assertRaises(ValidationError):
            self._wizard(self._invoice(self.partner_b), "OLD-SLIP")._create_payments()

    def _recover(self, invoices, number):
        wizard = self._wizard(invoices, number)
        wizard.write({"recover_bank_slip": True, "bank_slip_recovery_reason": "Corregir operación anulada"})
        return wizard._create_payments()

    def test_recover_cancelled_operation_and_block_old_reactivation(self):
        invoices = self._invoice(self.partner_a) | self._invoice(self.partner_b)
        old = self._wizard(invoices, "CANCEL-123")._create_payments()
        old.action_cancel()
        # Ordinary registration still preserves the strict historical policy.
        with self.assertRaises(ValidationError):
            self._wizard(invoices, "CANCEL-123")._create_payments()
        new = self._recover(invoices, "CANCEL-123")
        claim = self.env["ferreteria.bank.slip.registry"].sudo().search([
            ("number_normalized", "=", "cancel-123"),
        ])
        self.assertEqual(claim.payment_ids, new)
        self.assertEqual(set(claim.recovery_history[0]["payment_ids"]), set(old.ids))
        self.assertEqual(set(claim.recovery_history[0]["replacement_payment_ids"]), set(new.ids))
        self.assertEqual(set(old.mapped("state")), {"canceled"})
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            old.action_draft()
            old.action_post()

    def test_recover_deleted_payments_retains_audit(self):
        invoices = self._invoice(self.partner_a) | self._invoice(self.partner_b)
        old = self._wizard(invoices, "DELETED-123")._create_payments()
        original_id = old[0].id
        old.action_cancel()
        old.unlink()
        new = self._recover(invoices, "DELETED-123")
        claim = self.env["ferreteria.bank.slip.registry"].sudo().search([
            ("number_normalized", "=", "deleted-123"),
        ])
        self.assertEqual(claim.payment_ids, new)
        self.assertEqual(claim.recovery_history[0]["source_res_id"], original_id)

    def test_recovery_rejects_live_operation_and_rolls_back(self):
        self._wizard(self._invoice(self.partner_a), "LIVE-123")._create_payments()
        other = self._invoice(self.partner_b)
        count = self.env["account.payment"].search_count([])
        with self.assertRaises(ValidationError):
            self._recover(other, "LIVE-123")
        self.assertEqual(self.env["account.payment"].search_count([]), count)
        self.assertEqual(other.amount_residual, other.amount_total)

    def test_recovery_requires_reason_and_accounting_manager(self):
        invoice = self._invoice(self.partner_a)
        wizard = self._wizard(invoice, "PERM-123")
        wizard.recover_bank_slip = True
        with self.assertRaises(ValidationError):
            wizard._create_payments()
        wizard.bank_slip_recovery_reason = "Corregir anulación"
        user = self.env["res.users"].create({
            "name": "Bank slip billing user", "login": "bank_slip_billing_test",
            "company_id": self.env.company.id,
            "company_ids": [Command.set(self.env.companies.ids)],
            "groups_id": [Command.set([self.env.ref("account.group_account_invoice").id])],
        })
        with self.assertRaises(AccessError):
            wizard.with_user(user)._create_payments()

    def test_seven_invoices_grouped_and_legacy_duplicate_checker(self):
        invoices = self.env["account.move"]
        for partner in [self.partner_a] * 5 + [self.partner_b, self.partner_b]:
            invoices |= self._invoice(partner)
        wizard = self._wizard(invoices, "SEVEN-123")
        # The accounting kit propagates references before posting when an
        # effective date is present, exposing the legacy duplicate-popup hook.
        wizard.write({"group_payment": True, "effective_date": "2026-10-12"})
        payments = wizard._create_payments()
        self.assertTrue(payments)
        self.assertTrue(all(p.move_id.state == "posted" for p in payments))
        self.assertTrue(all(inv.amount_residual == 0 for inv in invoices))

    def test_public_button_recovers_with_cancelled_legacy_duplicates(self):
        invoices = self._invoice(self.partner_a) | self._invoice(self.partner_b)
        old = self._wizard(invoices, "PUBLIC-123")._create_payments()
        old.action_cancel()
        wizard = self._wizard(invoices, "PUBLIC-123")
        wizard.write({"recover_bank_slip": True, "bank_slip_recovery_reason": "Corregir operación anulada"})
        result = wizard.action_create_payments()
        self.assertNotEqual(result.get("res_model"), "account.dup.bank.reference.wizard")
        payments = self.env["account.payment"].search([("bank_reference", "=", "PUBLIC-123"), ("state", "!=", "canceled")])
        self.assertTrue(all(inv.amount_residual == 0 for inv in invoices), {
            "invoices": invoices.read(["amount_residual", "payment_state"]),
            "payments": payments.read(["amount", "state", "move_id"]),
            "moves": payments.move_id.read(["state", "date"]),
        })
