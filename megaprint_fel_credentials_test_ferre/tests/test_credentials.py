# -*- coding: utf-8 -*-

from unittest.mock import Mock, patch

from lxml import etree

from odoo.tests.common import TransactionCase


class TestMegaprintCredentials(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.pruebas_fel = True
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "FEL Credential Test",
                "code": "FCT",
                "type": "sale",
                "company_id": cls.company.id,
                "usuario_fel": " 1200&08122 ",
                "clave_fel": " key<&> ",
            }
        )

    def _result_from_action(self, action):
        return self.env[action["res_model"]].browse(action["res_id"])

    @patch(
        "odoo.addons.megaprint_fel_credentials_test_ferre.models.account_journal.requests.post"
    )
    def test_qa_success_uses_trimmed_xml_and_hides_token(self, mocked_post):
        response = Mock()
        response.status_code = 200
        response.content = (
            b"<?xml version='1.0' encoding='UTF-8'?>"
            b"<SolicitaTokenResponse><tipo_respuesta>0</tipo_respuesta>"
            b"<token>SECRET.JWT.TOKEN</token>"
            b"<vigencia>2026-12-22T00:00:00-06:00</vigencia>"
            b"</SolicitaTokenResponse>"
        )
        mocked_post.return_value = response

        action = self.journal.action_test_megaprint_credentials()
        result = self._result_from_action(action)

        self.assertEqual(result.status, "success")
        self.assertTrue(result.token_received)
        self.assertEqual(result.token_length, len("SECRET.JWT.TOKEN"))
        self.assertNotIn("SECRET.JWT.TOKEN", result.functional_description or "")

        payload = mocked_post.call_args.kwargs["data"]
        root = etree.fromstring(payload)
        self.assertEqual(root.findtext("usuario"), "1200&08122")
        self.assertEqual(root.findtext("apikey"), "key<&>")
        self.assertIn(b"1200&amp;08122", payload)
        self.assertIn(b"key&lt;&amp;&gt;", payload)

    @patch(
        "odoo.addons.megaprint_fel_credentials_test_ferre.models.account_journal.requests.post"
    )
    def test_production_is_blocked_without_http_call(self, mocked_post):
        self.company.pruebas_fel = False

        action = self.journal.action_test_megaprint_credentials()
        result = self._result_from_action(action)

        self.assertEqual(result.status, "blocked")
        self.assertEqual(result.functional_code, "LOCAL_PRODUCTION_BLOCKED")
        mocked_post.assert_not_called()

    @patch(
        "odoo.addons.megaprint_fel_credentials_test_ferre.models.account_journal.requests.post"
    )
    def test_invalid_credentials_are_reported_without_secret(self, mocked_post):
        response = Mock()
        response.status_code = 200
        response.content = (
            b"<?xml version='1.0' encoding='UTF-8'?>"
            b"<SolicitaTokenResponse><tipo_respuesta>1</tipo_respuesta>"
            b"<listado_errores><error><cod_error>002</cod_error>"
            b"<desc_error>Credenciales invalidas</desc_error></error></listado_errores>"
            b"</SolicitaTokenResponse>"
        )
        mocked_post.return_value = response

        action = self.journal.action_test_megaprint_credentials()
        result = self._result_from_action(action)

        self.assertEqual(result.status, "error")
        self.assertEqual(result.functional_code, "002")
        self.assertIn("Credenciales", result.functional_description)
        self.assertFalse(result.token_received)
        self.assertNotIn("key<&>", result.functional_description or "")
