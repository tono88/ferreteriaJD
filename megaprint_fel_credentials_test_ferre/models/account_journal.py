# -*- coding: utf-8 -*-

import hashlib
import logging
import re
import time

import requests
from lxml import etree

from odoo import _, fields, models


_logger = logging.getLogger(__name__)

QA_TOKEN_ENDPOINT = "https://dev2.api.ifacere-fel.com/api/solicitarToken"
REQUEST_TIMEOUT = (10, 30)
MAX_SAFE_DESCRIPTION = 1200


class AccountJournal(models.Model):
    _inherit = "account.journal"

    @staticmethod
    def _megaprint_mask_user(value):
        value = value or ""
        if not value:
            return "(vacío)"
        if len(value) <= 2:
            return "*" * len(value)
        if len(value) <= 4:
            return value[0] + ("*" * (len(value) - 2)) + value[-1]
        return value[:2] + ("*" * (len(value) - 4)) + value[-2:]

    @staticmethod
    def _megaprint_partial_sha256(value):
        if not value:
            return ""
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12].upper()

    @staticmethod
    def _megaprint_first_text(root, names):
        if root is None:
            return ""
        for name in names:
            nodes = root.xpath("//*[local-name()=$node_name]", node_name=name)
            for node in nodes:
                text = (node.text or "").strip()
                if text:
                    return text
        return ""

    @staticmethod
    def _megaprint_safe_description(value, secrets=None):
        text = str(value or "").strip()
        for secret in sorted(set(secrets or []), key=len, reverse=True):
            if secret:
                text = text.replace(secret, "[DATO PROTEGIDO]")
        text = re.sub(
            r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]+",
            "Bearer [TOKEN PROTEGIDO]",
            text,
        )
        text = re.sub(
            r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b",
            "[TOKEN PROTEGIDO]",
            text,
        )
        if len(text) > MAX_SAFE_DESCRIPTION:
            text = text[:MAX_SAFE_DESCRIPTION] + "…"
        return text

    @staticmethod
    def _megaprint_response_bytes(response):
        content = getattr(response, "content", b"") or b""
        if isinstance(content, str):
            content = content.encode("utf-8", errors="replace")
        if content:
            return content
        text = getattr(response, "text", "") or ""
        return text.encode("utf-8", errors="replace")

    def _megaprint_open_credentials_result(self, values):
        result = self.env["megaprint.fel.credentials.test.result"].create(values)
        return {
            "type": "ir.actions.act_window",
            "name": _("Resultado de prueba de credenciales FEL"),
            "res_model": "megaprint.fel.credentials.test.result",
            "view_mode": "form",
            "view_id": self.env.ref(
                "megaprint_fel_credentials_test_ferre.view_megaprint_fel_credentials_test_result_form"
            ).id,
            "res_id": result.id,
            "target": "new",
        }

    def action_test_megaprint_credentials(self):
        """Solicita únicamente un token QA y muestra un diagnóstico sin secretos.

        Este método no crea facturas, no contabiliza, no consume inventario y no
        modifica órdenes POS. La única escritura funcional es el registro
        temporal usado para mostrar el resultado en pantalla.
        """
        self.ensure_one()

        raw_user = self.usuario_fel or ""
        raw_api_key = self.clave_fel or ""
        clean_user = raw_user.strip()
        clean_api_key = raw_api_key.strip()
        user_edge_spaces = raw_user != clean_user
        api_key_edge_spaces = raw_api_key != clean_api_key
        masked_user = self._megaprint_mask_user(clean_user)
        user_hash = self._megaprint_partial_sha256(clean_user)
        api_key_hash = self._megaprint_partial_sha256(clean_api_key)

        common_values = {
            "journal_id": self.id,
            "tested_at": fields.Datetime.now(),
            "environment": "QA / pruebas" if self.company_id.pruebas_fel else "Producción",
            "endpoint": QA_TOKEN_ENDPOINT,
            "masked_user": masked_user,
            "user_length_raw": len(raw_user),
            "user_length_clean": len(clean_user),
            "api_key_length_raw": len(raw_api_key),
            "api_key_length_clean": len(clean_api_key),
            "user_has_edge_spaces": user_edge_spaces,
            "api_key_has_edge_spaces": api_key_edge_spaces,
            "user_sha256_partial": user_hash,
            "api_key_sha256_partial": api_key_hash,
            "token_received": False,
            "token_length": 0,
            "duration_ms": 0,
        }

        if not self.company_id.pruebas_fel:
            values = dict(
                common_values,
                status="blocked",
                functional_code="LOCAL_PRODUCTION_BLOCKED",
                functional_description=(
                    "La prueba fue bloqueada localmente porque la compañía no tiene "
                    "activado el modo de pruebas FEL. No se realizó ninguna llamada HTTP."
                ),
            )
            _logger.warning(
                "[FEL_CREDENTIALS_TEST] blocked journal_id=%s company_id=%s "
                "environment=production endpoint=%s user=%s user_len=%s api_key_len=%s",
                self.id,
                self.company_id.id,
                QA_TOKEN_ENDPOINT,
                masked_user,
                len(clean_user),
                len(clean_api_key),
            )
            return self._megaprint_open_credentials_result(values)

        missing = []
        if not clean_user:
            missing.append(_("Usuario FEL"))
        if not clean_api_key:
            missing.append(_("API key / Clave FEL"))
        if missing:
            values = dict(
                common_values,
                status="error",
                functional_code="LOCAL_MISSING_CREDENTIALS",
                functional_description=_("Faltan campos obligatorios: %s")
                % ", ".join(missing),
            )
            _logger.warning(
                "[FEL_CREDENTIALS_TEST] missing_credentials journal_id=%s "
                "endpoint=%s user=%s user_len=%s api_key_len=%s",
                self.id,
                QA_TOKEN_ENDPOINT,
                masked_user,
                len(clean_user),
                len(clean_api_key),
            )
            return self._megaprint_open_credentials_result(values)

        request_root = etree.Element("SolicitaTokenRequest")
        etree.SubElement(request_root, "usuario").text = clean_user
        etree.SubElement(request_root, "apikey").text = clean_api_key
        request_payload = etree.tostring(
            request_root,
            xml_declaration=True,
            encoding="UTF-8",
            standalone=False,
        )
        headers = {
            "Content-Type": "application/xml",
            "Accept": "application/xml",
        }

        started_at = time.monotonic()
        response = None
        try:
            response = requests.post(
                QA_TOKEN_ENDPOINT,
                data=request_payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            duration_ms = round((time.monotonic() - started_at) * 1000)
        except requests.Timeout:
            duration_ms = round((time.monotonic() - started_at) * 1000)
            values = dict(
                common_values,
                status="error",
                duration_ms=duration_ms,
                functional_code="NETWORK_TIMEOUT",
                functional_description=(
                    "Megaprint no respondió dentro del tiempo máximo configurado. "
                    "No se recibió token."
                ),
            )
            _logger.warning(
                "[FEL_CREDENTIALS_TEST] timeout journal_id=%s endpoint=%s user=%s "
                "user_len=%s api_key_len=%s user_hash=%s api_key_hash=%s duration_ms=%s",
                self.id,
                QA_TOKEN_ENDPOINT,
                masked_user,
                len(clean_user),
                len(clean_api_key),
                user_hash,
                api_key_hash,
                duration_ms,
            )
            return self._megaprint_open_credentials_result(values)
        except requests.RequestException as exc:
            duration_ms = round((time.monotonic() - started_at) * 1000)
            safe_error = self._megaprint_safe_description(
                exc, [raw_user, clean_user, raw_api_key, clean_api_key]
            )
            values = dict(
                common_values,
                status="error",
                duration_ms=duration_ms,
                functional_code="NETWORK_ERROR",
                functional_description=(
                    "No fue posible conectar con el endpoint de Megaprint. "
                    "Detalle seguro: %s" % safe_error
                ),
            )
            _logger.warning(
                "[FEL_CREDENTIALS_TEST] network_error journal_id=%s endpoint=%s "
                "user=%s user_len=%s api_key_len=%s user_hash=%s api_key_hash=%s "
                "duration_ms=%s error=%s",
                self.id,
                QA_TOKEN_ENDPOINT,
                masked_user,
                len(clean_user),
                len(clean_api_key),
                user_hash,
                api_key_hash,
                duration_ms,
                safe_error,
            )
            return self._megaprint_open_credentials_result(values)

        http_status = int(getattr(response, "status_code", 0) or 0)
        response_body = self._megaprint_response_bytes(response)
        parser = etree.XMLParser(
            resolve_entities=False,
            no_network=True,
            recover=False,
            huge_tree=False,
        )

        try:
            response_root = etree.fromstring(response_body, parser=parser)
        except (etree.XMLSyntaxError, ValueError, TypeError):
            values = dict(
                common_values,
                status="error",
                http_status=http_status,
                duration_ms=duration_ms,
                functional_code="INVALID_XML_RESPONSE",
                functional_description=(
                    "Megaprint respondió, pero el contenido no era un XML válido. "
                    "La respuesta completa no se muestra ni se registra para evitar "
                    "exponer información sensible."
                ),
            )
            _logger.warning(
                "[FEL_CREDENTIALS_TEST] invalid_xml journal_id=%s endpoint=%s "
                "user=%s user_len=%s api_key_len=%s user_hash=%s api_key_hash=%s "
                "http_status=%s duration_ms=%s response_bytes=%s",
                self.id,
                QA_TOKEN_ENDPOINT,
                masked_user,
                len(clean_user),
                len(clean_api_key),
                user_hash,
                api_key_hash,
                http_status,
                duration_ms,
                len(response_body),
            )
            return self._megaprint_open_credentials_result(values)

        token = self._megaprint_first_text(response_root, ["token"])
        response_type = self._megaprint_first_text(
            response_root, ["tipo_respuesta", "tipoRespuesta"]
        )
        functional_code = self._megaprint_first_text(
            response_root,
            ["cod_error", "codigo_error", "codigo", "code"],
        )
        description = self._megaprint_first_text(
            response_root,
            ["desc_error", "descripcion_error", "descripcion", "mensaje", "message"],
        )
        token_expiration = self._megaprint_first_text(
            response_root, ["vigencia", "fecha_vigencia", "expiracion"]
        )

        safe_description = self._megaprint_safe_description(
            description,
            [raw_user, clean_user, raw_api_key, clean_api_key, token],
        )

        if token and http_status == 200 and response_type in ("", "0", "00"):
            values = dict(
                common_values,
                status="success",
                http_status=http_status,
                duration_ms=duration_ms,
                functional_code=response_type or "0",
                functional_description=(
                    "Megaprint aceptó las credenciales y devolvió un token. "
                    "El token no se muestra, no se almacena en el diario y no se registra en el log."
                ),
                token_received=True,
                token_length=len(token),
                token_expiration=token_expiration,
            )
            _logger.info(
                "[FEL_CREDENTIALS_TEST] success journal_id=%s company_id=%s "
                "environment=qa endpoint=%s user=%s user_len=%s api_key_len=%s "
                "user_edge_spaces=%s api_key_edge_spaces=%s user_hash=%s "
                "api_key_hash=%s http_status=%s functional_code=%s "
                "token_received=true token_len=%s duration_ms=%s",
                self.id,
                self.company_id.id,
                QA_TOKEN_ENDPOINT,
                masked_user,
                len(clean_user),
                len(clean_api_key),
                user_edge_spaces,
                api_key_edge_spaces,
                user_hash,
                api_key_hash,
                http_status,
                response_type or "0",
                len(token),
                duration_ms,
            )
            return self._megaprint_open_credentials_result(values)

        if not functional_code:
            functional_code = response_type or (
                "HTTP_%s" % http_status if http_status else "TOKEN_NOT_RECEIVED"
            )
        if not safe_description:
            safe_description = (
                "Megaprint no devolvió un token ni una descripción funcional legible."
            )

        values = dict(
            common_values,
            status="error",
            http_status=http_status,
            duration_ms=duration_ms,
            functional_code=functional_code,
            functional_description=safe_description,
            token_received=False,
            token_length=0,
            token_expiration=token_expiration,
        )
        _logger.warning(
            "[FEL_CREDENTIALS_TEST] rejected journal_id=%s company_id=%s "
            "environment=qa endpoint=%s user=%s user_len=%s api_key_len=%s "
            "user_edge_spaces=%s api_key_edge_spaces=%s user_hash=%s "
            "api_key_hash=%s http_status=%s functional_code=%s "
            "description=%s token_received=false duration_ms=%s",
            self.id,
            self.company_id.id,
            QA_TOKEN_ENDPOINT,
            masked_user,
            len(clean_user),
            len(clean_api_key),
            user_edge_spaces,
            api_key_edge_spaces,
            user_hash,
            api_key_hash,
            http_status,
            functional_code,
            safe_description,
            duration_ms,
        )
        return self._megaprint_open_credentials_result(values)
