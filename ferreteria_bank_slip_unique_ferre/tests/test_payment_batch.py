from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestPaymentBatchBankSlip(AccountTestInvoicingCommon):
    def _invoice(self, partner):
        invoice = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": partner.id,
            "invoice_date": "2026-10-01",
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
