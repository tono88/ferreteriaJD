from odoo.tests import TransactionCase, tagged

from ..models.res_partner import normalize_nit


@tagged("post_install", "-at_install")
class TestPartnerNitSearch(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {"name": "CLIENTE PRUEBA NIT POS", "vat": "5489632-1"}
        )
        cls.other_partner = cls.env["res.partner"].create(
            {"name": "CLIENTE NIT DISTINTO", "vat": "1234567-8"}
        )
        cls.final_consumer = cls.env["res.partner"].create(
            {"name": "CONSUMIDOR FINAL", "vat": "CF"}
        )

    def _search_nit(self, value):
        return self.env["res.partner"].search(
            [("pos_nit_search_normalized", "=", value)]
        )

    def test_normalization_does_not_change_vat(self):
        self.assertEqual(normalize_nit("5489632-1"), "54896321")
        self.assertEqual(normalize_nit("54896321"), "54896321")
        self.assertEqual(normalize_nit("548 9632 1"), "54896321")
        self.assertEqual(self.partner.vat, "5489632-1")

    def test_exact_nit_with_hyphen(self):
        self.assertEqual(self._search_nit("5489632-1"), self.partner)

    def test_exact_nit_without_hyphen(self):
        self.assertEqual(self._search_nit("54896321"), self.partner)

    def test_exact_nit_with_spaces(self):
        self.assertEqual(self._search_nit("548 9632 1"), self.partner)

    def test_different_nit_is_not_returned(self):
        self.assertNotIn(self.other_partner, self._search_nit("54896321"))

    def test_partial_nit_is_not_returned(self):
        self.assertFalse(self._search_nit("5489632"))

    def test_final_consumer(self):
        matches = self._search_nit("CF")
        self.assertIn(self.final_consumer, matches)
        self.assertTrue(all(normalize_nit(partner.vat) == "cf" for partner in matches))
