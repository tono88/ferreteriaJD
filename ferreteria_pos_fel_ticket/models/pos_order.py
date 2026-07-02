# -*- coding: utf-8 -*-

import base64
import binascii
import logging
from datetime import date, datetime
from urllib.parse import quote

from lxml import etree

from odoo import api, fields, models, _
from odoo.exceptions import AccessError
from odoo.tools.misc import formatLang

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = "pos.order"

    # Candidate field names are intentionally broad.  The active Ferretería
    # integration uses firma_fel / serie_fel / numero_fel / documento_xml_fel,
    # while this keeps the ticket compatible with small naming differences in
    # other Megaprint builds without creating duplicate FEL fields.
    _FEL_FIELD_CANDIDATES = {
        "authorization": (
            "firma_fel",
            "fel_uuid",
            "uuid_fel",
            "numero_autorizacion_fel",
            "numero_autorizacion",
            "fel_authorization",
            "authorization_number",
        ),
        "series": (
            "serie_fel",
            "fel_serie",
            "fel_series",
            "serie_dte",
        ),
        "number": (
            "numero_fel",
            "fel_numero",
            "fel_number",
            "numero_dte",
        ),
        "certifier": (
            "certificador_fel",
            "nombre_certificador",
            "fel_certifier",
            "certifier_name",
        ),
        "certifier_vat": (
            "nit_certificador",
            "nit_certificador_fel",
            "fel_certifier_vat",
            "certifier_vat",
        ),
        "certification_datetime": (
            "fecha_certificacion_fel",
            "fel_fecha_certificacion",
            "fecha_hora_certificacion",
            "fecha_certificacion",
            "certification_datetime",
        ),
        "xml": (
            "documento_xml_fel",
            "xml_certificado",
            "fel_xml",
            "xml_fel",
            "xml_dte",
            "certified_xml",
        ),
        "qr": (
            "qr_fel",
            "fel_qr",
            "qr_code_fel",
            "fel_qr_url",
            "qr_url",
            "url_qr",
            "sat_validation_url",
            "verification_url",
        ),
    }

    @api.model
    def get_fel_ticket_data_for_pos(self, order_id=False, pos_reference=False, uuid=False):
        """Return normalized invoice/FEL data for the POS receipt screen.

        The POS user first locates the order with their normal permissions.  A
        sudo record is then used only to read the linked invoice fields, because
        cashier users often do not have direct Accounting read access.
        """
        order = self.browse()
        if order_id:
            order = self.browse(int(order_id)).exists()
        if not order and uuid:
            order = self.search([("uuid", "=", uuid)], limit=1)
        if not order and pos_reference:
            order = self.search([("pos_reference", "=", pos_reference)], limit=1)
        if not order:
            return {
                "enabled": False,
                "status": "not_found",
                "message": _("No fue posible localizar la orden en el servidor."),
            }

        try:
            order.check_access_rights("read")
            order.check_access_rule("read")
        except AccessError:
            return {
                "enabled": False,
                "status": "access_denied",
                "message": _("No tiene permisos para consultar esta orden."),
            }

        return order.sudo()._get_fel_ticket_data()

    def _get_fel_ticket_data(self):
        self.ensure_one()
        move = self.account_move.sudo()
        company = self.company_id.sudo()
        partner = self.partner_id.sudo()
        xml_data = self._extract_fel_xml_data(move) if move else {}

        if not move:
            return {
                "enabled": False,
                "status": "not_invoiced",
                "certified": False,
                "message": _("La orden no tiene una factura vinculada."),
            }

        authorization = xml_data.get("authorization") or self._first_field_value(
            move, self._FEL_FIELD_CANDIDATES["authorization"]
        )
        series = xml_data.get("series") or self._first_field_value(
            move, self._FEL_FIELD_CANDIDATES["series"]
        )
        number = xml_data.get("number") or self._first_field_value(
            move, self._FEL_FIELD_CANDIDATES["number"]
        )
        certification_datetime = xml_data.get("certification_datetime") or self._first_field_value(
            move, self._FEL_FIELD_CANDIDATES["certification_datetime"]
        )
        certifier_name = xml_data.get("certifier_name") or self._first_field_value(
            move, self._FEL_FIELD_CANDIDATES["certifier"]
        )
        certifier_vat = xml_data.get("certifier_vat") or self._first_field_value(
            move, self._FEL_FIELD_CANDIDATES["certifier_vat"]
        )

        # The current project uses Megaprint.  These values are only fallbacks;
        # XML or explicit invoice fields always take precedence.
        certifier_name = certifier_name or "MEGAPRINT, S.A."
        certifier_vat = certifier_vat or "50510231"

        qr_image_src, qr_value = self._get_qr_data(move)
        issue_datetime = (
            xml_data.get("issue_datetime")
            or self._format_datetime_value(self.date_order)
            or self._format_datetime_value(move.invoice_date)
        )
        certification_datetime = self._format_datetime_value(certification_datetime)

        emitter_name = xml_data.get("emitter_name") or company.name or ""
        commercial_name = (
            xml_data.get("commercial_name")
            or self.config_id.name
            or emitter_name
        )
        emitter_vat = xml_data.get("emitter_vat") or company.vat or ""
        emitter_address = (
            xml_data.get("emitter_address")
            or self._get_establishment_address(move)
            or self._record_address(company.partner_id)
        )

        customer_name = xml_data.get("customer_name") or partner.name or _("Consumidor Final")
        customer_vat = xml_data.get("customer_vat") or partner.vat or "CF"
        customer_address = xml_data.get("customer_address") or self._record_address(partner) or ""

        document_type_label = self._get_document_type_label(move, xml_data.get("document_type"))
        cashier = self._get_ticket_cashier_name()
        certified = bool(authorization)

        ticket_lines = self._get_ticket_lines()
        ticket_payments = self._get_ticket_payments()

        return {
            "enabled": True,
            "status": "certified" if certified else "pending",
            "certified": certified,
            "message": "" if certified else _("Factura creada; certificación FEL pendiente."),
            "move_id": move.id,
            "move_name": move.name or "",
            "document_type": document_type_label,
            "authorization": self._to_text(authorization),
            "series": self._to_text(series),
            "number": self._to_text(number),
            "issue_datetime": issue_datetime,
            "certification_datetime": certification_datetime,
            "certifier_name": self._to_text(certifier_name),
            "certifier_vat": self._to_text(certifier_vat),
            "emitter_name": self._to_text(emitter_name),
            "commercial_name": self._to_text(commercial_name),
            "emitter_vat": self._to_text(emitter_vat),
            "emitter_address": self._to_text(emitter_address),
            "customer_name": self._to_text(customer_name),
            "customer_vat": self._to_text(customer_vat),
            "customer_address": self._to_text(customer_address),
            "cashier": self._to_text(cashier),
            "pos_name": self.config_id.name or "",
            "order_reference": self.pos_reference or self.name or "",
            "company_logo_url": (
                f"/web/image/res.company/{company.id}/logo" if company.logo else ""
            ),
            "qr_image_src": qr_image_src,
            "qr_value": qr_value,
            "lines": ticket_lines,
            "payments": ticket_payments,
            "amount_untaxed": move.amount_untaxed,
            "amount_tax": move.amount_tax,
            "amount_total": move.amount_total,
            "amount_paid": self.amount_paid,
            "amount_return": self.amount_return,
            "amount_untaxed_formatted": self._format_amount(move.amount_untaxed),
            "amount_tax_formatted": self._format_amount(move.amount_tax),
            "amount_total_formatted": self._format_amount(move.amount_total),
            "amount_paid_formatted": self._format_amount(self.amount_paid),
            "amount_return_formatted": self._format_amount(self.amount_return),
            "receipt_header": self._plain_config_text(self.config_id.receipt_header),
            "receipt_footer": self._plain_config_text(self.config_id.receipt_footer),
        }

    def _get_ticket_cashier_name(self):
        self.ensure_one()
        if "employee_id" in self._fields and self.employee_id:
            return self.employee_id.name
        return self.user_id.name or ""

    def _get_ticket_lines(self):
        self.ensure_one()
        values = []
        for line in self.lines:
            line_total = self._line_total_included(line)
            values.append({
                "name": line.full_product_name or line.product_id.display_name or "",
                "quantity": line.qty,
                "quantity_display": self._format_quantity(line.qty),
                "unit_price": line.price_unit,
                "unit_price_formatted": self._format_amount(line.price_unit),
                "discount": line.discount or 0.0,
                "discount_display": self._format_quantity(line.discount or 0.0),
                "line_total": line_total,
                "line_total_formatted": self._format_amount(line_total),
                "customer_note": getattr(line, "customer_note", False) or "",
            })
        return values

    def _get_ticket_payments(self):
        self.ensure_one()
        values = []
        for payment in self.payment_ids:
            if "is_change" in payment._fields and payment.is_change:
                continue
            values.append({
                "name": payment.payment_method_id.name or "",
                "amount": payment.amount,
                "amount_formatted": self._format_amount(payment.amount),
            })
        return values

    def _line_total_included(self, line):
        for field_name in ("price_subtotal_incl", "price_subtotal"):
            if field_name in line._fields:
                value = line[field_name]
                if value is not False:
                    return value
        return line.qty * line.price_unit * (1.0 - (line.discount or 0.0) / 100.0)

    def _format_amount(self, amount):
        self.ensure_one()
        return formatLang(self.env, amount or 0.0, currency_obj=self.currency_id)

    @staticmethod
    def _format_quantity(value):
        value = value or 0.0
        if float(value).is_integer():
            return str(int(value))
        return ("%.4f" % value).rstrip("0").rstrip(".")

    @staticmethod
    def _plain_config_text(value):
        if not value:
            return ""
        # receipt_header/footer are plain text in standard POS, but a few custom
        # modules store HTML.  Keep the ticket readable in both cases.
        text = str(value)
        return (
            text.replace("<br/>", "\n")
            .replace("<br>", "\n")
            .replace("<br />", "\n")
        )

    def _get_document_type_label(self, move, xml_type=False):
        code = (xml_type or "").upper()
        if code in ("NCRE", "NDEB") or move.move_type == "out_refund":
            return _("Nota de Crédito Electrónica")
        return _("Factura Electrónica")

    def _get_establishment_address(self, move):
        journal = move.journal_id
        for field_name in (
            "direccion",
            "fel_address_id",
            "address_id",
            "direccion_establecimiento_id",
            "establishment_address_id",
        ):
            if field_name not in journal._fields:
                continue
            value = journal[field_name]
            if isinstance(value, models.BaseModel):
                address = self._record_address(value)
                if address:
                    return address
            elif value:
                return self._to_text(value)
        return ""

    @staticmethod
    def _record_address(record):
        if not record:
            return ""
        parts = []
        for field_name in ("street", "street2", "city"):
            if field_name in record._fields and record[field_name]:
                parts.append(str(record[field_name]).strip())
        if "state_id" in record._fields and record.state_id:
            parts.append(record.state_id.name)
        if "zip" in record._fields and record.zip:
            parts.append(str(record.zip).strip())
        if "country_id" in record._fields and record.country_id:
            parts.append(record.country_id.name)
        return ", ".join(part for part in parts if part)

    def _get_qr_data(self, move):
        for field_name in self._FEL_FIELD_CANDIDATES["qr"]:
            if field_name not in move._fields:
                continue
            value = move[field_name]
            if not value:
                continue
            field = move._fields[field_name]
            if field.type == "binary":
                return f"/web/image/account.move/{move.id}/{field_name}", ""
            text = self._to_text(value).strip()
            if text.startswith("data:image/"):
                return text, ""
            if text:
                return f"/report/barcode/QR/{quote(text, safe='')}", text
        return "", ""

    def _extract_fel_xml_data(self, move):
        if not move:
            return {}
        xml_value = self._first_field_value(move, self._FEL_FIELD_CANDIDATES["xml"], raw=True)
        if not xml_value:
            return {}
        xml_bytes = self._decode_xml_value(xml_value)
        if not xml_bytes:
            return {}
        try:
            parser = etree.XMLParser(
                resolve_entities=False,
                no_network=True,
                recover=True,
                huge_tree=False,
            )
            root = etree.fromstring(xml_bytes, parser=parser)
        except (etree.XMLSyntaxError, ValueError, TypeError):
            _logger.warning("No fue posible interpretar el XML FEL de la factura %s", move.id)
            return {}

        authorization_node = self._xpath_first(root, "//*[local-name()='NumeroAutorizacion']")
        certification_node = self._xpath_first(root, "//*[local-name()='FechaHoraCertificacion']")
        certifier_name_node = self._xpath_first(root, "//*[local-name()='NombreCertificador']")
        certifier_vat_node = self._xpath_first(root, "//*[local-name()='NITCertificador']")
        general_node = self._xpath_first(root, "//*[local-name()='DatosGenerales']")
        emitter_node = self._xpath_first(root, "//*[local-name()='Emisor']")
        receiver_node = self._xpath_first(root, "//*[local-name()='Receptor']")
        emitter_address_node = self._xpath_first(root, "//*[local-name()='DireccionEmisor']")
        receiver_address_node = self._xpath_first(root, "//*[local-name()='DireccionReceptor']")

        return {
            "authorization": self._node_text(authorization_node),
            "series": authorization_node.get("Serie", "") if authorization_node is not None else "",
            "number": authorization_node.get("Numero", "") if authorization_node is not None else "",
            "certification_datetime": self._node_text(certification_node),
            "certifier_name": self._node_text(certifier_name_node),
            "certifier_vat": self._node_text(certifier_vat_node),
            "issue_datetime": general_node.get("FechaHoraEmision", "") if general_node is not None else "",
            "document_type": general_node.get("Tipo", "") if general_node is not None else "",
            "emitter_name": emitter_node.get("NombreEmisor", "") if emitter_node is not None else "",
            "commercial_name": emitter_node.get("NombreComercial", "") if emitter_node is not None else "",
            "emitter_vat": emitter_node.get("NITEmisor", "") if emitter_node is not None else "",
            "emitter_address": self._xml_address(emitter_address_node),
            "customer_name": receiver_node.get("NombreReceptor", "") if receiver_node is not None else "",
            "customer_vat": receiver_node.get("IDReceptor", "") if receiver_node is not None else "",
            "customer_address": self._xml_address(receiver_address_node),
        }

    @staticmethod
    def _xpath_first(root, expression):
        values = root.xpath(expression)
        return values[0] if values else None

    @staticmethod
    def _node_text(node):
        return (node.text or "").strip() if node is not None else ""

    @staticmethod
    def _xml_address(node):
        if node is None:
            return ""
        parts = []
        for child_name in ("Direccion", "CodigoPostal", "Municipio", "Departamento", "Pais"):
            values = node.xpath("./*[local-name()=$name]/text()", name=child_name)
            if values and values[0] and values[0].strip():
                parts.append(values[0].strip())
        return ", ".join(parts)

    @staticmethod
    def _decode_xml_value(value):
        if isinstance(value, bytes):
            raw = value
        else:
            raw = str(value).encode("utf-8", errors="ignore")
        stripped = raw.lstrip()
        if stripped.startswith(b"<"):
            return stripped
        try:
            decoded = base64.b64decode(raw, validate=False).lstrip()
            return decoded if decoded.startswith(b"<") else b""
        except (binascii.Error, ValueError):
            return b""

    @staticmethod
    def _first_field_value(record, candidates, raw=False):
        if not record:
            return False
        for field_name in candidates:
            if field_name not in record._fields:
                continue
            value = record[field_name]
            if not value:
                continue
            if raw:
                return value
            if isinstance(value, models.BaseModel):
                return value.display_name
            return value
        return False

    @staticmethod
    def _to_text(value):
        if value in (False, None):
            return ""
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="ignore")
        return str(value)

    def _format_datetime_value(self, value):
        if not value:
            return ""
        if isinstance(value, datetime):
            local_value = fields.Datetime.context_timestamp(self, value)
            return local_value.strftime("%d/%m/%Y %H:%M:%S")
        if isinstance(value, date):
            return value.strftime("%d/%m/%Y")
        text = self._to_text(value).strip()
        if "T" in text:
            text = text.replace("T", " ", 1)
        return text
