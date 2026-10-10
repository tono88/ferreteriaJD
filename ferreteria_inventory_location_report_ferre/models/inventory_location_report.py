import base64
import io

import xlsxwriter

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class InventoryLocationReportDownload(models.TransientModel):
    _name = "ferreteria.inventory.location.report.download"
    _description = "Descarga temporal de inventario por ubicacion"

    file_data = fields.Binary(required=True, readonly=True, attachment=False)
    file_name = fields.Char(required=True, readonly=True)


class StockQuant(models.Model):
    _inherit = "stock.quant"

    @api.model
    def _location_report_domain(self, domain):
        if not isinstance(domain, list):
            raise UserError(_("El dominio recibido no es valido."))
        return domain

    @api.model
    def _location_report_quants(self, domain):
        """Search as the current user so ACLs and record rules remain effective."""
        self.check_access("read")
        return self.search(
            self._location_report_domain(domain),
            order="location_id, product_id, id",
        )

    @api.model
    def _location_report_lines(self, domain):
        lines = []
        for quant in self._location_report_quants(domain):
            product = quant.product_id
            lines.append(
                {
                    "code": product.default_code or "",
                    "product": product.name or "",
                    "location": quant.location_id.complete_name or quant.location_id.name or "",
                    "quantity": quant.quantity,
                    "quantity_display": (f"{quant.quantity:.6f}".rstrip("0").rstrip(".") or "0"),
                    "uom": quant.product_uom_id.name or "",
                }
            )
        return lines

    @api.model
    def action_print_location_report(self, domain, filter_summary=None, domain_display=None):
        domain = self._location_report_domain(domain)
        lines = self._location_report_lines(domain)
        generated_at = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        return self.env.ref(
            "ferreteria_inventory_location_report_ferre.action_inventory_location_pdf"
        ).report_action(
            self.env["stock.quant"],
            data={
                "domain": domain,
                "filter_summary": filter_summary or _("Sin filtros adicionales"),
                "domain_display": domain_display or "[]",
                "lines": lines,
                "record_count": len(lines),
                "generated_at": generated_at.strftime("%d/%m/%Y %H:%M:%S"),
            },
            config=False,
        )

    @api.model
    def action_export_location_report_xlsx(
        self, domain, filter_summary=None, domain_display=None
    ):
        lines = self._location_report_lines(domain)
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet("Inventario por ubicacion")

        title_format = workbook.add_format(
            {"bold": True, "font_size": 14, "align": "center"}
        )
        subtitle_format = workbook.add_format(
            {"bold": True, "font_size": 11, "align": "center"}
        )
        meta_format = workbook.add_format({"font_color": "#555555", "italic": True})
        header_format = workbook.add_format(
            {
                "bold": True,
                "font_color": "#FFFFFF",
                "bg_color": "#714B67",
                "border": 1,
                "align": "center",
            }
        )
        text_format = workbook.add_format({"border": 1})
        qty_format = workbook.add_format({"border": 1, "num_format": "#,##0.######"})

        sheet.merge_range("A1:E1", "DISTRIBUIDORA Y FERRETERIA JB", title_format)
        sheet.merge_range("A2:E2", "Inventario por ubicacion", subtitle_format)
        generated_at = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        sheet.merge_range(
            "A3:E3",
            _("Generado: %s") % generated_at.strftime("%d/%m/%Y %H:%M:%S"),
            meta_format,
        )
        sheet.merge_range(
            "A4:E4", _("Filtros: %s") % (filter_summary or _("Sin filtros adicionales")), meta_format
        )
        headers = [_('Codigo'), _('Producto'), _('Ubicacion'), _('Existencia'), _('UDM')]
        for col, header in enumerate(headers):
            sheet.write(5, col, header, header_format)
        for row, line in enumerate(lines, start=6):
            sheet.write(row, 0, line["code"], text_format)
            sheet.write(row, 1, line["product"], text_format)
            sheet.write(row, 2, line["location"], text_format)
            sheet.write_number(row, 3, line["quantity"], qty_format)
            sheet.write(row, 4, line["uom"], text_format)
        sheet.set_column("A:A", 16)
        sheet.set_column("B:B", 42)
        sheet.set_column("C:C", 38)
        sheet.set_column("D:D", 15)
        sheet.set_column("E:E", 16)
        sheet.freeze_panes(6, 0)
        sheet.autofilter(5, 0, max(5, 5 + len(lines)), 4)
        workbook.close()
        output.seek(0)

        filename = "inventario_por_ubicacion_%s.xlsx" % fields.Date.context_today(self)
        download = self.env["ferreteria.inventory.location.report.download"].create(
            {
                "file_data": base64.b64encode(output.read()),
                "file_name": filename,
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": (
                "/web/content/ferreteria.inventory.location.report.download/"
                f"{download.id}/file_data/{filename}?download=true"
            ),
            "target": "self",
        }

