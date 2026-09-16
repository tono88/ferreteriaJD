# -*- coding: utf-8 -*-
import base64
import html
import uuid
from datetime import datetime, time

import pytz
import requests
from lxml import etree

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.addons.fel_megaprint_annul_patch_ferre.models.account_move import (
    _env_is_test,
    _get_creds,
    _request_token,
    _retornar_pdf_v2,
    _save_pdf_on_move,
    _to_draft_then_cancel,
)


DTE_ANNUL_NS = "http://www.sat.gob.gt/dte/fel/0.1.0"


class AccountMove(models.Model):
    _inherit = "account.move"

    def _ferreteria_fel_original_move(self):
        self.ensure_one()
        return self.factura_original_id or self.reversed_entry_id

    def dte_documento(self):
        """Bridge Odoo 18's reversal link to the legacy FEL reference field."""
        for move in self:
            if move.move_type != "out_refund":
                continue
            original = move._ferreteria_fel_original_move()
            if not original:
                raise UserError(_("La nota de crédito FEL no tiene factura de origen."))
            if not original.firma_fel or not original.serie_fel or not original.numero_fel:
                raise UserError(_("La factura de origen no posee una certificación FEL completa."))
            if not move.motivo_fel or not move.motivo_fel.strip() or move.motivo_fel.strip() == "-":
                raise UserError(_("Indique un motivo real para la nota de crédito FEL."))
            if not move.factura_original_id:
                move.factura_original_id = original
        return super().dte_documento()

    def _ferreteria_fel_original_xml_root(self):
        self.ensure_one()
        for field_name in ("resultado_xml_fel", "documento_xml_fel"):
            payload = getattr(self, field_name, False)
            if not payload:
                continue
            try:
                raw = base64.b64decode(payload)
                root = etree.fromstring(raw)
                if (
                    root is not None
                    and root.xpath("//*[local-name()='DatosGenerales']")
                    and root.xpath("//*[local-name()='Emisor']")
                    and root.xpath("//*[local-name()='Receptor']")
                ):
                    return root
            except Exception:
                continue
        return None

    def _ferreteria_fel_original_values(self):
        self.ensure_one()
        root = self._ferreteria_fel_original_xml_root()
        if root is not None:
            emission = root.xpath("string(//*[local-name()='DatosGenerales'][1]/@FechaHoraEmision)")
            issuer = root.xpath("string(//*[local-name()='Emisor'][1]/@NITEmisor)")
            receiver = root.xpath("string(//*[local-name()='Receptor'][1]/@IDReceptor)")
        else:
            emission = issuer = receiver = ""

        issuer = issuer or (self.company_id.vat or "").replace("-", "")
        receiver = receiver or (
            self.partner_id.nit_facturacion_fel
            or self.partner_id.vat
            or "CF"
        ).replace("-", "")

        if not emission:
            invoice_date = self.invoice_date or fields.Date.context_today(self)
            company_tz = self.env.context.get("tz") or self.env.user.tz or "America/Guatemala"
            timezone = pytz.timezone(company_tz)
            emission = timezone.localize(datetime.combine(invoice_date, time.min)).isoformat(timespec="seconds")
        return emission, issuer, receiver

    def dte_anulacion(self):
        """Build an annulment with exact certified identifiers and real local time."""
        self.ensure_one()
        if not self.firma_fel:
            raise UserError(_("La factura no posee autorización FEL para anular."))
        if not self.motivo_fel or not self.motivo_fel.strip() or self.motivo_fel.strip() == "-":
            raise UserError(_("Indique un motivo real para la anulación FEL."))

        emission, issuer, receiver = self._ferreteria_fel_original_values()
        if not issuer or not receiver:
            raise UserError(_("No fue posible determinar el emisor o receptor del DTE original."))

        local_tz_name = self.env.context.get("tz") or self.env.user.tz or "America/Guatemala"
        local_tz = pytz.timezone(local_tz_name)
        now_utc = pytz.utc.localize(fields.Datetime.now())
        annulled_at = now_utc.astimezone(local_tz).isoformat(timespec="seconds")

        nsmap = {
            "ds": "http://www.w3.org/2000/09/xmldsig#",
            "dte": DTE_ANNUL_NS,
        }
        dte_ns = "{%s}" % DTE_ANNUL_NS
        root = etree.Element(dte_ns + "GTAnulacionDocumento", Version="0.1", nsmap=nsmap)
        sat = etree.SubElement(root, dte_ns + "SAT")
        annulment = etree.SubElement(sat, dte_ns + "AnulacionDTE", ID="DatosCertificados")
        etree.SubElement(
            annulment,
            dte_ns + "DatosGenerales",
            ID="DatosAnulacion",
            NumeroDocumentoAAnular=self.firma_fel,
            NITEmisor=issuer,
            IDReceptor=receiver,
            FechaEmisionDocumentoAnular=emission,
            FechaHoraAnulacion=annulled_at,
            MotivoAnulacion=self.motivo_fel.strip(),
        )
        return root

    def _ferreteria_fel_annul_request_id(self):
        """Use an idempotency key distinct from the original FACT request key."""
        self.ensure_one()
        seed = "account.move:%s:fel:annul:%s" % (self.id, self.firma_fel or "")
        return str(uuid.uuid5(uuid.NAMESPACE_OID, seed)).upper()

    def action_annul_fel_megaprint(self):
        """Submit the annulment with an operation-specific request identifier."""
        for move in self:
            if not move.requiere_certificacion():
                raise UserError(_("Este documento no requiere certificación FEL."))
            if not move.firma_fel:
                raise UserError(_("La factura no posee firma FEL; no se puede anular."))

            usuario, apikey, modo = _get_creds(move)
            is_test = _env_is_test(move, modo)
            api_host = "dev2.api.ifacere-fel.com" if is_test else "apiv2.ifacere-fel.com"
            firma_host = ("dev." if is_test else "") + "api.soluciones-mega.com"
            token, _token_url, _token_response = _request_token(api_host, usuario, apikey)

            xml_sin_firma = etree.tostring(
                move.dte_anulacion(), encoding="UTF-8"
            ).decode("utf-8")
            headers = {
                "Content-Type": "application/xml",
                "authorization": "Bearer " + token,
                "Accept": "application/xml",
            }
            request_id = move._ferreteria_fel_annul_request_id()
            sign_payload = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<FirmaDocumentoRequest id="{rid}"><xml_dte><![CDATA[{xml}]]>'
                '</xml_dte></FirmaDocumentoRequest>'
            ).format(rid=request_id, xml=xml_sin_firma)
            response = requests.post(
                "https://%s/api/solicitaFirma" % firma_host,
                data=sign_payload.encode("utf-8"), headers=headers, timeout=60,
            )
            try:
                sign_xml = etree.XML((response.text or "").encode("utf-8"))
            except Exception as exc:
                raise UserError(_("Respuesta inválida al firmar la anulación.")) from exc
            signed_nodes = sign_xml.xpath("//*[local-name()='xml_dte']")
            if not signed_nodes or not signed_nodes[0].text:
                raise UserError(_("Megaprint no devolvió el XML de anulación firmado."))
            xml_firmado = html.unescape(signed_nodes[0].text)

            annul_payload = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<AnulaDocumentoXMLRequest id="{rid}"><xml_dte><![CDATA[{xml}]]>'
                '</xml_dte></AnulaDocumentoXMLRequest>'
            ).format(rid=request_id, xml=xml_firmado)
            response = requests.post(
                "https://%s/api/anularDocumentoXML" % api_host,
                data=annul_payload.encode("utf-8"), headers=headers, timeout=60,
            )
            try:
                annul_xml = etree.XML((response.text or "").encode("utf-8"))
            except Exception as exc:
                raise UserError(_("Respuesta inválida al enviar la anulación.")) from exc
            if annul_xml.xpath("//*[local-name()='listado_errores']"):
                raise UserError(_("Megaprint devolvió errores al anular el DTE."))

            original_uuid = move.firma_fel
            annul_uuid_nodes = annul_xml.xpath("//*[local-name()='uuid']")
            annul_uuid = (
                annul_uuid_nodes and (annul_uuid_nodes[0].text or "").strip()
            ) or False
            pdf_bytes = None
            try:
                if original_uuid:
                    pdf_bytes = _retornar_pdf_v2(api_host, token, original_uuid)
                if not pdf_bytes and annul_uuid:
                    pdf_bytes = _retornar_pdf_v2(
                        api_host, token, annul_uuid, xml_firmado
                    )
            except Exception:
                pdf_bytes = None
            _save_pdf_on_move(
                move, pdf_bytes,
                "fel_anulacion_%s.pdf" % (original_uuid or annul_uuid or "doc"),
            )
            if not _to_draft_then_cancel(move):
                raise UserError(_(
                    "FEL anulado en Megaprint, pero no fue posible cancelar la factura en Odoo."
                ))
            move.write({"fel_annulled": True})
            move.message_post(body=_("FEL anulado correctamente en Megaprint QA."))
        return True
