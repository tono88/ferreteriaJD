# -*- coding: utf-8 -*-
from datetime import datetime, time

from odoo import models, _


class PosSalesSummaryXlsx(models.AbstractModel):
    _name = "report.pos_sales_summary_report_ferre.report_pos_sales_summary_xlsx"
    _table = "report_pos_sales_summary_xlsx_ferre"
    _inherit = "report.report_xlsx_ferre.abstract"
    _description = "Reporte XLSX: Resumen de ventas POS"

    def generate_xlsx_report(self, workbook, data, orders):
        report = self.env[
            "report.pos_sales_summary_report_ferre.report_pos_sales_summary"
        ]
        values = report._get_report_values(docids=None, data=data or {})
        grouped = values.get("grouped", [])
        lines_linear = values.get("lines_linear", [])
        linear = values.get("order_by_internal_correlative", False)

        sheet = workbook.add_worksheet(_("Ventas POS")[:31])
        bold = workbook.add_format({"bold": True})
        money = workbook.add_format({"num_format": "#,##0.00"})
        date_format = workbook.add_format({"num_format": "dd/mm/yyyy"})
        wrap = workbook.add_format({"text_wrap": True})

        sheet.set_column("A:A", 15)
        sheet.set_column("B:B", 30)
        sheet.set_column("C:C", 18)
        sheet.set_column("D:D", 34)
        sheet.set_column("E:G", 14)
        sheet.set_column("H:H", 30)

        row = 0
        sheet.write(row, 0, _("Reporte de Ventas POS"), bold)
        row += 1
        sheet.write(
            row,
            0,
            _("Del: %s  Al: %s")
            % (values.get("data", {}).get("date_from", ""), values.get("data", {}).get("date_to", "")),
        )
        row += 1
        sheet.write(row, 0, _("Zona horaria: %s") % values.get("report_timezone", ""))
        row += 2

        headers = [
            _("Fecha documento"),
            _("Cliente"),
            _("No. interno"),
            _("Factura/Firma FEL"),
            _("Contado"),
            _("Otros"),
            _("Total"),
            _("Observación"),
        ]
        for column, header in enumerate(headers):
            sheet.write(row, column, header, bold)
        row += 1

        lines = lines_linear if linear else [
            line for group in grouped for line in group.get("lines", [])
        ]
        for line in lines:
            document_date = line.get("document_date")
            if document_date:
                sheet.write_datetime(
                    row,
                    0,
                    datetime.combine(document_date, time.min),
                    date_format,
                )
            else:
                sheet.write(row, 0, "-")
            sheet.write(row, 1, line.get("partner") or "")
            sheet.write(row, 2, line.get("correlative") or "")
            sheet.write(row, 3, line.get("invoice") or "", wrap)
            sheet.write_number(row, 4, line.get("contado") or 0.0, money)
            sheet.write_number(row, 5, line.get("credito") or 0.0, money)
            sheet.write_number(row, 6, line.get("total") or 0.0, money)
            sheet.write(row, 7, line.get("observation") or "", wrap)
            row += 1

        row += 1
        sheet.write(row, 3, _("Totales"), bold)
        sheet.write_number(row, 4, values.get("total_contado") or 0.0, money)
        sheet.write_number(row, 5, values.get("total_credito") or 0.0, money)
        sheet.write_number(row, 6, values.get("total_general") or 0.0, money)
        sheet.freeze_panes(5, 0)
        sheet.autofilter(4, 0, max(row - 2, 4), 7)
