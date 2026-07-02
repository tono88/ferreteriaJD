# -*- encoding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round

import logging
_logger = logging.getLogger(__name__)

from datetime import datetime, timedelta
import base64
from os import path
from lxml import etree
import requests
import html
import uuid
import re


class AccountInvoice(models.Model):
    _inherit = "account.move"

    pdf_fel = fields.Binary('PDF FEL', copy=False)
    name_pdf_fel = fields.Char('Nombre archivo PDF FEL', default='fel.pdf', size=32)

    # ---------------------------------------------------------------------
    # Helpers robustos para leer/aplicar Serie/Número de xml_dte o del name
    # ---------------------------------------------------------------------

    def _fel_parse_na(self, xml_text):
        """
        Devuelve dict {'firma': <uuid>, 'serie': <serie>, 'numero': <numero>}
        ó None si no encuentra el nodo NumeroAutorizacion.
        """
        try:
            ns = {'dte': 'http://www.sat.gob.gt/dte/fel/0.2.0'}
            root = etree.XML(xml_text.encode('utf-8'))

            # 1) con namespace
            nodes = root.xpath('.//dte:NumeroAutorizacion', namespaces=ns)
            if not nodes:
                # 2) sin namespace (algunos certificadores lo devuelven “plano”)
                nodes = root.xpath('.//NumeroAutorizacion')

            if not nodes:
                return None

            na = nodes[0]
            # Atributos pueden venir “Serie/Numero” o “serie/numero”
            serie = na.get('Serie') or na.get('serie') or ''
            numero = na.get('Numero') or na.get('numero') or ''
            firma = (na.text or '').strip()

            # sanea
            serie = serie.strip() if isinstance(serie, str) else str(serie or '')
            numero = str(numero).strip()
            firma = firma.strip()

            return {'firma': firma, 'serie': serie, 'numero': numero}
        except Exception as e:
            _logger.warning("[MEGAPRINT] _fel_parse_na fallo: %s", e)
            return None

    def _fel_apply_na(self, move, na):
        """
        Aplica firma/serie/numero a la factura y renombra name=SERIE-NUMERO.
        """
        vals = {}
        if na.get('firma') and not getattr(move, 'firma_fel', False):
            vals['firma_fel'] = na['firma']
        if na.get('serie'):
            vals['serie_fel'] = na['serie']
        if na.get('numero'):
            vals['numero_fel'] = na['numero']

        if vals:
            move.write(vals)

        # Renombrar a SERIE-NUMERO si procede (y si no tiene nombre definitivo)
        if na.get('serie') and na.get('numero'):
            if not move.name or move.name == "/" or move.name.startswith("PEND-"):
                move.name = f"{na['serie']}-{na['numero']}"

    def _fel_sync_from_name_if_needed(self, move):
        """
        Si el name ya está en formato SERIE-NUMERO y los campos están vacíos,
        sincroniza serie_fel / numero_fel desde ahí (plan B).
        """
        if (not getattr(move, 'serie_fel', False) or not getattr(move, 'numero_fel', False)) and move.name:
            m = re.match(r"^([A-Z0-9]+)-(\d+)$", move.name or "")
            if m:
                move.write({'serie_fel': m.group(1), 'numero_fel': m.group(2)})

    # --- Helper principal: aplica NumeroAutorizacion del xml_dte y renombra name a SERIE-NUMERO ---
    def _fel_apply_from_xml(self, factura, xml_certificado_text):
        try:
            na = self._fel_parse_na(xml_certificado_text)
            if not na:
                return False
            self._fel_apply_na(factura, na)
            return True
        except Exception as e:
            _logger.warning("[MEGAPRINT] _fel_apply_from_xml fallo: %s", e)
            return False


    def _fel_safe_filename_base(self, factura):
        value = factura.name or "factura_%s" % factura.id
        value = value.replace("/", "_").replace("\\", "_")
        return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_.") or "factura_%s" % factura.id

    def _fel_store_certified_xml(self, factura, xml_certificado_text):
        """Replace the preliminary signed XML with the final certified DTE.

        ``megaprint_fel_block_post_safe_ferre`` attaches ``documento_xml_fel``
        to the chatter after certification. Storing the certified XML here
        ensures that attachment is the final DTE containing
        ``NumeroAutorizacion``, not merely the emitter-signed preliminary XML.
        """
        if not xml_certificado_text:
            return False
        if isinstance(xml_certificado_text, bytes):
            xml_bytes = xml_certificado_text
            xml_text = xml_certificado_text.decode("utf-8")
        else:
            xml_text = str(xml_certificado_text)
            xml_bytes = xml_text.encode("utf-8")

        # Validate before replacing the stored document.
        na = self._fel_parse_na(xml_text)
        if not na or not na.get("firma") or not na.get("serie") or not na.get("numero"):
            raise UserError("El XML recuperado no contiene una autorización FEL completa.")

        vals = {}
        if "documento_xml_fel" in factura._fields:
            vals["documento_xml_fel"] = base64.b64encode(xml_bytes)
        if "documento_xml_fel_name" in factura._fields:
            vals["documento_xml_fel_name"] = "%s_fel_cert.xml" % self._fel_safe_filename_base(factura)[:18]
        if vals:
            factura.write(vals)
        _logger.info(
            "[MEGAPRINT] XML certificado almacenado move_id=%s serie=%s numero=%s",
            factura.id, na.get("serie"), na.get("numero"),
        )
        return True

    def _fel_extract_response_error(self, root):
        descriptions = []
        for xpath in (
            "//*[local-name()='desc_error']",
            "//*[local-name()='descripcion_errores']",
            "//*[local-name()='descripcion']",
        ):
            for node in root.xpath(xpath):
                text = (node.text or "").strip()
                if text and text not in descriptions:
                    descriptions.append(text)
        return "; ".join(descriptions) or "Respuesta FEL sin detalle de error."

    def action_recover_megaprint_certified_xml(self):
        """Recover and store an already certified XML without recertifying."""
        for factura in self:
            if not getattr(factura, "firma_fel", False):
                raise UserError("La factura no tiene UUID de autorización FEL para recuperar.")
            usuario = (getattr(factura.journal_id, "usuario_fel", False) or "").strip()
            apikey = (getattr(factura.journal_id, "clave_fel", False) or "").strip()
            if not usuario or not apikey:
                raise UserError("El diario no tiene usuario y API key FEL configurados.")

            base_url = "https://apiv2.ifacere-fel.com/api"
            if getattr(factura.company_id, "pruebas_fel", False):
                base_url = "https://dev2.api.ifacere-fel.com/api"

            token_root = etree.Element("SolicitaTokenRequest")
            etree.SubElement(token_root, "usuario").text = usuario
            etree.SubElement(token_root, "apikey").text = apikey
            try:
                response = requests.post(
                    base_url + "/solicitarToken",
                    data=etree.tostring(token_root, encoding="UTF-8", xml_declaration=True),
                    headers={"Content-Type": "application/xml"},
                    timeout=(5, 30),
                )
                response.raise_for_status()
                token_xml = etree.fromstring(response.content)
            except (requests.RequestException, etree.XMLSyntaxError) as exc:
                raise UserError("No se pudo solicitar el token FEL: %s" % exc)
            token = (token_xml.findtext(".//token") or "").strip()
            if not token:
                raise UserError(self._fel_extract_response_error(token_xml))

            request_root = etree.Element("RetornaXMLRequest")
            etree.SubElement(request_root, "uuid").text = factura.firma_fel
            try:
                response = requests.post(
                    base_url + "/retornarXML",
                    data=etree.tostring(request_root, encoding="UTF-8", xml_declaration=True),
                    headers={
                        "Content-Type": "application/xml",
                        "authorization": "Bearer " + token,
                    },
                    timeout=(5, 30),
                )
                response.raise_for_status()
                result_xml = etree.fromstring(response.content)
            except (requests.RequestException, etree.XMLSyntaxError) as exc:
                raise UserError("No se pudo recuperar el XML certificado FEL: %s" % exc)

            nodes = result_xml.xpath("//*[local-name()='xml_dte']")
            if not nodes or not (nodes[0].text or "").strip():
                raise UserError(self._fel_extract_response_error(result_xml))
            xml_certificado = nodes[0].text
            na = self._fel_parse_na(xml_certificado)
            if not na or na.get("firma") != factura.firma_fel:
                raise UserError("El XML recuperado no corresponde al UUID de esta factura.")

            self._fel_store_certified_xml(factura, xml_certificado)
            self._fel_apply_na(factura, na)
            attachment_ids = []
            if "documento_xml_fel" in factura._fields and factura.documento_xml_fel:
                attachment = self.env["ir.attachment"].sudo().create({
                    "name": getattr(factura, "documento_xml_fel_name", False) or "%s_fel_cert.xml" % self._fel_safe_filename_base(factura)[:18],
                    "datas": factura.documento_xml_fel,
                    "res_model": "account.move",
                    "res_id": factura.id,
                    "mimetype": "application/xml",
                })
                attachment_ids.append(attachment.id)
            factura.message_post(
                body="<b>XML certificado FEL recuperado y almacenado.</b>",
                attachment_ids=attachment_ids,
            )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "FEL",
                "message": "El XML certificado fue recuperado y almacenado sin recertificar la factura.",
                "type": "success",
                "sticky": False,
            },
        }

    # ---------------------------------------------------------------------
    # Flujo principal de certificación (idempotente por id)
    # ---------------------------------------------------------------------
    def certificar_megaprint(self):
        import time

        _logger.warning('[MEGAPRINT] Ejecutando certificar_megaprint')
        for factura in self:
            if not getattr(factura.journal_id, 'usuario_fel', False):
                continue

            # Si ya está certificada, no recertificar
            if getattr(factura, 'firma_fel', False):
                raise UserError("La factura ya fue validada, por lo que no puede ser validada nuevamente")

            dte = factura.dte_documento()
            if dte is None:
                continue

            xml_sin_firma = etree.tostring(dte, encoding="UTF-8").decode("utf-8")

            # --- ambientes
            request_url = "apiv2"; request_path = ""; request_url_firma = ""
            if getattr(factura.company_id, 'pruebas_fel', False):
                request_url = "dev2.api"; request_path = ""; request_url_firma = "dev."

            # --- token
            headers = {"Content-Type": "application/xml"}
            data = f'<?xml version="1.0" encoding="UTF-8"?><SolicitaTokenRequest><usuario>{factura.journal_id.usuario_fel}</usuario><apikey>{factura.journal_id.clave_fel}</apikey></SolicitaTokenRequest>'
            r = requests.post(f'https://{request_url}.ifacere-fel.com/{request_path}api/solicitarToken',
                              data=data.encode('utf-8'), headers=headers, timeout=(5, 30))
            resultadoXML = etree.XML(r.text.encode('utf-8'))
            if not resultadoXML.xpath("//token"):
                raise UserError(r.text)
            token = resultadoXML.xpath("//token")[0].text

            uuid_req = str(uuid.uuid5(uuid.NAMESPACE_OID, str(factura.id))).upper()
            headers = {"Content-Type": "application/xml", "authorization": "Bearer " + token}

            # --- PRECHECK: si ya existe por ID, no reenvíes
            try:
                vdata = f'<?xml version="1.0" encoding="UTF-8"?><VerificaDocumentoRequest id="{uuid_req}"/>'
                rv = requests.post(f'https://{request_url}.ifacere-fel.com/{request_path}api/verificarDocumento',
                                   data=vdata.encode('utf-8'), headers=headers, timeout=(5, 12))
                vxml = etree.XML(rv.text.encode('utf-8'))
                vnode = vxml.xpath("//xml_dte")
                if vnode:
                    self._fel_store_certified_xml(factura, vnode[0].text)
                    if self._fel_apply_from_xml(factura, vnode[0].text):
                        # por si algún otro flujo ya fijó el name: SERIE-NUMERO
                        self._fel_sync_from_name_if_needed(factura)
                        _logger.info("[MEGAPRINT] Documento ya certificado (verificarDocumento por id=%s).", uuid_req)
                        return True
            except Exception as e:
                _logger.warning("[MEGAPRINT] precheck verificarDocumento falló: %s", e)

            # --- FIRMAR
            data = f'<?xml version="1.0" encoding="UTF-8"?><FirmaDocumentoRequest id="{uuid_req}"><xml_dte><![CDATA[{xml_sin_firma}]]></xml_dte></FirmaDocumentoRequest>'
            r = requests.post(f'https://{request_url_firma}api.soluciones-mega.com/api/solicitaFirma',
                              data=data.encode('utf-8'), headers=headers, timeout=(5, 30))
            resultadoXML = etree.XML(r.text.encode('utf-8'))
            if not resultadoXML.xpath("//xml_dte"):
                raise UserError(r.text)
            xml_con_firma = resultadoXML.xpath("//xml_dte")[0].text

            # Guarda XML firmado (trazabilidad)
            if hasattr(factura, 'documento_xml_fel'):
                try:
                    factura.documento_xml_fel = base64.b64encode(xml_con_firma.encode('utf-8'))
                except Exception:
                    pass

            # --- REGISTRAR (idempotente por id)
            data = f'<?xml version="1.0" encoding="UTF-8"?><RegistraDocumentoRequest id="{uuid_req}"><xml_dte><![CDATA[{xml_con_firma}]]></xml_dte></RegistraDocumentoRequest>'
            r = requests.post(f'https://{request_url}.ifacere-fel.com/{request_path}api/registrarDocumentoUuid',
                              data=data.encode('utf-8'), headers=headers, timeout=(5, 30))
            resultadoXML = etree.XML(r.text.encode('utf-8'))

            # Guarda respuesta cruda (trazabilidad)
            if hasattr(factura, 'resultado_xml_fel'):
                try:
                    factura.resultado_xml_fel = base64.b64encode(etree.tostring(resultadoXML))
                except Exception:
                    pass

            # --- Ventana agresiva (10 s) de recuperación de xml_dte sin re-enviar ---
            t0 = time.time()
            xml_certificado = None
            # 0) ¿vino en registrar?
            node = resultadoXML.xpath("//xml_dte")
            if node:
                xml_certificado = node[0].text

            while xml_certificado is None and time.time() - t0 < 10:
                try:
                    # 1) verificarDocumento por id
                    vreq = f'<?xml version="1.0" encoding="UTF-8"?><VerificaDocumentoRequest id="{uuid_req}"/>'
                    rv = requests.post(f'https://{request_url}.ifacere-fel.com/{request_path}api/verificarDocumento',
                                       data=vreq.encode('utf-8'), headers=headers, timeout=(5, 12))
                    vxml = etree.XML(rv.text.encode('utf-8'))

                    # persistir temprano el uuid si vino sin xml_dte
                    uuid_dte = (vxml.findtext(".//uuid") or "").strip()
                    if uuid_dte and not getattr(factura, 'firma_fel', False):
                        try:
                            factura.firma_fel = uuid_dte
                            factura.flush()
                        except Exception:
                            pass

                    vnode = vxml.xpath("//xml_dte")
                    if vnode:
                        xml_certificado = vnode[0].text
                        break

                    # 2) si hay uuid, intentar retornarXML
                    if uuid_dte:
                        rx = f'<?xml version="1.0" encoding="UTF-8"?><RetornaXMLRequest><uuid>{uuid_dte}</uuid></RetornaXMLRequest>'
                        rr = requests.post(f'https://{request_url}.ifacere-fel.com/{request_path}api/retornarXML',
                                           data=rx.encode('utf-8'), headers=headers, timeout=(5, 15))
                        vxml2 = etree.XML(rr.text.encode('utf-8'))
                        if vxml2.xpath("//xml_dte"):
                            xml_certificado = vxml2.xpath("//xml_dte")[0].text
                            break
                except Exception as e:
                    _logger.warning("[MEGAPRINT] recuperación rápida falló: %s", e)
                time.sleep(1)

            # --- Aplicar resultado como hace infile ---
            if xml_certificado:
                self._fel_store_certified_xml(factura, xml_certificado)
                applied = self._fel_apply_from_xml(factura, xml_certificado)
                # plan B: por si otro flujo ya armó el name SERIE-NUMERO
                self._fel_sync_from_name_if_needed(factura)
                if not applied:
                    raise UserError("No se pudo aplicar NumeroAutorizacion del xml_dte (id=%s)." % uuid_req)
            else:
                # no duplicar: no reenvíes; devuelve error limpio
                #raise UserError("No se recibió xml_dte del certificador para id=%s; no se reenvió para evitar duplicados." % uuid_req)
                # Intentar extraer info de error del primer registrar
            # Mensaje genérico por si no logramos leer nada
                msg = (
                    "No se recibió xml_dte del certificador para id=%s; "
                    "no se reenvió para evitar duplicados."
                ) % uuid_req

                # Intentar extraer tipo_respuesta y listado_errores
                try:
                    tipo_resp = (resultadoXML.findtext(".//tipo_respuesta") or "").strip()
                except Exception:
                    tipo_resp = ""

                errores = []
                try:
                    for e in resultadoXML.xpath("//listado_errores//descripcion_errores | //descripcion_errores"):
                        if e is not None and (e.text or "").strip():
                            errores.append(e.text.strip())
                except Exception:
                    pass

                if tipo_resp and tipo_resp != "0":
                    if errores:
                        msg = "Error FEL (tipo_respuesta=%s) para id=%s:\n%s" % (
                            tipo_resp, uuid_req, "\n".join(errores)
                        )
                    else:
                        # Aquí usamos etree, pero SIN volver a importarlo
                        msg = "Error FEL sin xml_dte (tipo_respuesta=%s) para id=%s.\nXML:\n%s" % (
                            tipo_resp,
                            uuid_req,
                            etree.tostring(resultadoXML, encoding="unicode")
                        )

                raise UserError(msg)

        return True

    def action_post(self):
        res = super(AccountInvoice, self).action_post()
        for factura in self:
            if factura.journal_id.usuario_fel:
                factura.certificar_megaprint()
        return res

    def action_cancel(self):
        result = super(AccountInvoice, self).action_cancel()
        for factura in self:
            if factura.journal_id.usuario_fel and factura.firma_fel:
                dte = factura.dte_anulacion()
                _logger.warning(dte)
                if dte:
                    xml_sin_firma = etree.tostring(dte, encoding="UTF-8").decode("utf-8")

                    request_url = "apiv2"
                    request_path = ""
                    request_url_firma = ""
                    if factura.company_id.pruebas_fel:
                        request_url = "dev2.api"
                        request_path = ""
                        request_url_firma = "dev."

                    headers = {"Content-Type": "application/xml"}
                    data = '<?xml version="1.0" encoding="UTF-8"?><SolicitaTokenRequest><usuario>{}</usuario><apikey>{}</apikey></SolicitaTokenRequest>'.format(
                        factura.journal_id.usuario_fel, factura.journal_id.clave_fel)
                    r = requests.post('https://' + request_url + '.ifacere-fel.com/' + request_path + 'api/solicitarToken',
                                      data=data.encode('utf-8'), timeout=(5, 30), headers=headers)
                    resultadoXML = etree.XML(bytes(r.text, encoding='utf-8'))

                    if len(resultadoXML.xpath("//token")) > 0:
                        token = resultadoXML.xpath("//token")[0].text
                        uuid_factura = str(uuid.uuid5(uuid.NAMESPACE_OID, str(factura.id))).upper()

                        headers = {"Content-Type": "application/xml", "authorization": "Bearer " + token}

                        # --- PRECHECK Idempotencia: verificar si ya existe por ID (evita duplicados) ---
                        try:
                            vdata = '<?xml version="1.0" encoding="UTF-8"?><VerificaDocumentoRequest id="{}"/>'.format(uuid_factura)
                            rv = requests.post('https://' + request_url + '.ifacere-fel.com/' + request_path + 'api/verificarDocumento',
                                               data=vdata.encode('utf-8'), headers=headers, timeout=(5, 15))
                            vxml = etree.XML(rv.text.encode('utf-8'))
                            vnode = vxml.xpath("//xml_dte")
                            if vnode:
                                xml_certificado = vnode[0].text
                                xml_certificado_root = etree.XML(bytes(xml_certificado, encoding='utf-8'))
                                numero_autorizacion = xml_certificado_root.find(".//{http://www.sat.gob.gt/dte/fel/0.2.0}NumeroAutorizacion")
                                if numero_autorizacion is not None:
                                    factura.firma_fel = numero_autorizacion.text
                                    factura.serie_fel = numero_autorizacion.get("Serie")
                                    factura.numero_fel = numero_autorizacion.get("Numero")
                                    _logger.info("[FEL] Documento ya certificado (verificarDocumento por id=%s), se evita reenvío.", uuid_factura)
                                    return
                        except Exception as e:
                            _logger.warning("[FEL] verificarDocumento precheck falló: %s", e)
                        data = '<?xml version="1.0" encoding="UTF-8"?><FirmaDocumentoRequest id="{}"><xml_dte><![CDATA[{}]]></xml_dte></FirmaDocumentoRequest>'.format(
                            uuid_factura, xml_sin_firma)
                        r = requests.post('https://' + request_url_firma + 'api.soluciones-mega.com/api/solicitaFirma',
                                          data=data.encode('utf-8'), timeout=(5, 30), headers=headers)
                        _logger.warning(r.text)
                        resultadoXML = etree.XML(bytes(r.text, encoding='utf-8'))
                        if len(resultadoXML.xpath("//xml_dte")) > 0:
                            xml_con_firma = html.unescape(resultadoXML.xpath("//xml_dte")[0].text)

                            headers = {"Content-Type": "application/xml", "authorization": "Bearer " + token}
                            data = '<?xml version="1.0" encoding="UTF-8"?><AnulaDocumentoXMLRequest id="{}"><xml_dte><![CDATA[{}]]></xml_dte></AnulaDocumentoXMLRequest>'.format(
                                uuid_factura, xml_con_firma)
                            _logger.warning(data)
                            r = requests.post('https://' + request_url + '.ifacere-fel.com/' + request_path + 'api/anularDocumentoXML',
                                              data=data.encode('utf-8'), timeout=(5, 30), headers=headers)
                            resultadoXML = etree.XML(bytes(r.text, encoding='utf-8'))

                            if len(resultadoXML.xpath("//listado_errores")) > 0:
                                raise UserError(r.text)
                        else:
                            raise UserError(r.text)
                    else:
                        raise UserError(r.text)

        return result


class AccountJournal(models.Model):
    _inherit = "account.journal"

    usuario_fel = fields.Char('Usuario FEL', copy=False)
    clave_fel = fields.Char('Clave FEL', copy=False)
    codigo_establecimiento_fel = fields.Char('Codigo Establecimiento FEL', copy=False)
    tipo_documento_fel = fields.Selection([
        ('FACT', 'FACT'), ('FCAM', 'FCAM'), ('FPEQ', 'FPEQ'), ('FCAP', 'FCAP'),
        ('FESP', 'FESP'), ('NABN', 'NABN'), ('RDON', 'RDON'), ('RECI', 'RECI'),
        ('NDEB', 'NDEB'), ('NCRE', 'NCRE')
    ], 'Tipo de Documento FEL', copy=False)


class ResCompany(models.Model):
    _inherit = "res.company"

    frases_fel = fields.Text('Frases FEL')
    adenda_fel = fields.Text('Adenda FEL')
    pruebas_fel = fields.Boolean('Modo de Pruebas FEL')
