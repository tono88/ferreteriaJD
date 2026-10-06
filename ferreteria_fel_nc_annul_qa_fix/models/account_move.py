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

    @staticmethod
    def _ferreteria_xml_response(response, stage):
        """Parse the original HTTP bytes to preserve UTF-8 exactly."""
        try:
            response.raise_for_status()
            return etree.fromstring(response.content)
        except requests.RequestException as exc:
            raise UserError(
                _("Error HTTP durante %s (HTTP %s).")
                % (stage, response.status_code or 0)
            ) from exc
        except etree.XMLSyntaxError as exc:
            raise UserError(
                _("Respuesta XML inválida durante %s (HTTP %s).")
                % (stage, response.status_code or 0)
            ) from exc

    @staticmethod
    def _ferreteria_response_details(root):
        codes = []
        descriptions = []
        for node in root.xpath("//*[local-name()='cod_error']"):
            value = (node.text or "").strip()
            if value and value not in codes:
                codes.append(value)
        for node in root.xpath("//*[local-name()='desc_error']"):
            value = (node.text or "").strip()
            if value and value not in descriptions:
                descriptions.append(value)
        response_type = root.xpath(
            "string(//*[local-name()='tipo_respuesta'][1])"
        ).strip()
        return codes, descriptions, response_type

    @staticmethod
    def _ferreteria_inner_xml(node):
        return html.unescape((node.text or "").strip())

    def action_annul_fel_megaprint(self):
        """Submit one UTF-8-safe annulment and mark it only after acceptance."""
        for move in self:
            if not move.firma_fel:
                raise UserError(_("La factura no posee autorización FEL para anular."))
            if move.fel_annulled:
                raise UserError(_("El DTE ya está marcado como anulado en Odoo."))
            if (
                not move.motivo_fel
                or not move.motivo_fel.strip()
                or move.motivo_fel.strip() == "-"
            ):
                raise UserError(_("Indique un motivo real para la anulación FEL."))

            usuario, apikey, modo = _get_creds(move)
            is_test = _env_is_test(move, modo)
            api_host = "dev2.api.ifacere-fel.com" if is_test else "apiv2.ifacere-fel.com"
            sign_host = ("dev." if is_test else "") + "api.soluciones-mega.com"
            headers = {"Content-Type": "application/xml", "Accept": "application/xml"}

            token_root = etree.Element("SolicitaTokenRequest")
            etree.SubElement(token_root, "usuario").text = usuario
            etree.SubElement(token_root, "apikey").text = apikey
            token_response = requests.post(
                "https://%s/api/solicitarToken" % api_host,
                data=etree.tostring(token_root, encoding="UTF-8", xml_declaration=True),
                headers=headers,
                timeout=60,
            )
            token_xml = move._ferreteria_xml_response(
                token_response, "autenticación FEL"
            )
            token = token_xml.xpath("string(//*[local-name()='token'][1])").strip()
            if not token:
                codes, descriptions, _response_type = (
                    move._ferreteria_response_details(token_xml)
                )
                raise UserError(
                    _("MegaPrint rechazó la autenticación FEL: %s %s")
                    % (
                        ", ".join(codes) or "SIN_CODIGO",
                        "; ".join(descriptions) or "",
                    )
                )

            auth_headers = dict(headers, authorization="Bearer " + token)
            request_id = move._ferreteria_fel_annul_request_id()
            unsigned_xml = etree.tostring(move.dte_anulacion(), encoding="UTF-8")

            sign_root = etree.Element("FirmaDocumentoRequest", id=request_id)
            etree.SubElement(sign_root, "xml_dte").text = etree.CDATA(
                unsigned_xml.decode("utf-8")
            )
            sign_response = requests.post(
                "https://%s/api/solicitaFirma" % sign_host,
                data=etree.tostring(sign_root, encoding="UTF-8", xml_declaration=True),
                headers=auth_headers,
                timeout=60,
            )
            sign_xml = move._ferreteria_xml_response(
                sign_response, "firma de anulación FEL"
            )
            signed_nodes = sign_xml.xpath("//*[local-name()='xml_dte']")
            if not signed_nodes or not (signed_nodes[0].text or "").strip():
                codes, descriptions, _response_type = (
                    move._ferreteria_response_details(sign_xml)
                )
                raise UserError(
                    _("MegaPrint rechazó la firma de anulación: %s %s")
                    % (
                        ", ".join(codes) or "SIN_CODIGO",
                        "; ".join(descriptions) or "",
                    )
                )
            signed_xml = move._ferreteria_inner_xml(signed_nodes[0])

            annul_root = etree.Element("AnulaDocumentoXMLRequest", id=request_id)
            etree.SubElement(annul_root, "xml_dte").text = etree.CDATA(signed_xml)
            annul_response = requests.post(
                "https://%s/api/anularDocumentoXML" % api_host,
                data=etree.tostring(annul_root, encoding="UTF-8", xml_declaration=True),
                headers=auth_headers,
                timeout=60,
            )
            annul_xml = move._ferreteria_xml_response(
                annul_response, "anulación FEL"
            )
            codes, descriptions, response_type = move._ferreteria_response_details(
                annul_xml
            )
            if annul_xml.xpath("//*[local-name()='listado_errores']") or response_type == "1":
                raise UserError(
                    _("MegaPrint rechazó la anulación: %s %s")
                    % (
                        ", ".join(codes) or "SIN_CODIGO",
                        "; ".join(descriptions) or "",
                    )
                )

            original_uuid = move.firma_fel
            annul_uuid = annul_xml.xpath(
                "string(//*[local-name()='uuid'][1])"
            ).strip()

            attachment_model = self.env["ir.attachment"].sudo()
            attachment_model.create({
                "name": "fel_anulacion_firmada_%s.xml" % original_uuid,
                "datas": base64.b64encode(signed_xml.encode("utf-8")),
                "res_model": "account.move",
                "res_id": move.id,
                "mimetype": "application/xml",
            })
            attachment_model.create({
                "name": "fel_anulacion_respuesta_%s.xml" % original_uuid,
                "datas": base64.b64encode(annul_response.content),
                "res_model": "account.move",
                "res_id": move.id,
                "mimetype": "application/xml",
            })

            # The remote annulment is irreversible once accepted. Persist the
            # accepted state before optional PDF/local cancellation work. Tests
            # can suppress the safety commit to keep fixtures transactional.
            move.write({"fel_annulled": True})
            move.message_post(body=_(
                "MegaPrint aceptó la anulación FEL. UUID de anulación: %s."
            ) % (annul_uuid or "no informado"))
            if not self.env.context.get("fel_skip_safety_commit"):
                self.env.cr.commit()

            saved_pdf = False
            try:
                pdf_bytes = _retornar_pdf_v2(
                    api_host, token, annul_uuid or original_uuid, signed_xml
                )
                saved_pdf = _save_pdf_on_move(
                    move,
                    pdf_bytes,
                    "fel_anulacion_%s.pdf" % (annul_uuid or original_uuid),
                )
            except Exception:
                saved_pdf = False

            locally_cancelled = _to_draft_then_cancel(move)
            if not locally_cancelled:
                move.message_post(body=_(
                    "El DTE fue anulado en MegaPrint, pero la factura no pudo cancelarse localmente."
                ))
            move.message_post(body=_(
                "FEL anulado correctamente en MegaPrint. UUID de anulación: %s. %s %s"
            ) % (
                annul_uuid or "no informado",
                "PDF actualizado." if saved_pdf else "PDF no actualizado automáticamente.",
                "Factura cancelada en Odoo." if locally_cancelled else "Cancelación local pendiente.",
            ))
        return True
