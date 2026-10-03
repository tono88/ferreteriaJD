import base64
import io

import xlsxwriter

from odoo import _, fields, models
from odoo.exceptions import AccessError, UserError


class FerreteriaMovementHistoryExportWizard(models.TransientModel):
    _name = "ferreteria.movement.history.export.wizard"
    _description = "Exportar historial de movimientos"

    date_from = fields.Date(string="Desde")
    date_to = fields.Date(string="Hasta")
    warehouse_ids = fields.Many2many("stock.warehouse", string="Almacenes")
    product_ids = fields.Many2many("product.product", string="Productos")
    file_data = fields.Binary(readonly=True)
    file_name = fields.Char(readonly=True)

    def _allowed_warehouses(self):
        user = self.env.user
        warehouses = self.env["stock.warehouse"].search([
            ("active", "=", True),
            ("company_id", "in", self.env.companies.ids),
        ])
        if user.ferreteria_scope_enforced:
            warehouses &= user.ferreteria_allowed_warehouse_ids
        return warehouses

    def _selected_warehouses(self):
        allowed = self._allowed_warehouses()
        selected = self.warehouse_ids or allowed
        if selected - allowed:
            raise AccessError(_("No puede consultar almacenes fuera de su ámbito autorizado."))
        if not selected:
            raise UserError(_("No hay almacenes autorizados para este reporte."))
        return selected

    def _line_warehouse(self, line, warehouses):
        picking_warehouse = line.move_id.picking_type_id.warehouse_id
        if picking_warehouse:
            return picking_warehouse if picking_warehouse in warehouses else False
        source_path = {int(value) for value in (line.location_id.parent_path or "").split("/") if value}
        destination_path = {int(value) for value in (line.location_dest_id.parent_path or "").split("/") if value}
        for warehouse in warehouses:
            if (
                warehouse.view_location_id.id in source_path
                or warehouse.view_location_id.id in destination_path
            ):
                return warehouse
        return False

    def _get_lines(self):
        self.ensure_one()
        warehouses = self._selected_warehouses()
        domain = [("state", "=", "done")]
        if self.date_from:
            domain.append(("date", ">=", fields.Datetime.to_string(fields.Datetime.start_of(self.date_from, "day"))))
        if self.date_to:
            domain.append(("date", "<", fields.Datetime.to_string(fields.Datetime.add(fields.Datetime.start_of(self.date_to, "day"), days=1))))
        if self.product_ids:
            domain.append(("product_id", "in", self.product_ids.ids))
        location_ids = self.env["stock.location"].search([
            "|",
            ("id", "child_of", warehouses.mapped("view_location_id").ids),
            ("usage", "in", ["supplier", "customer", "inventory", "transit"]),
        ]).ids
        domain += ["|", ("location_id", "in", location_ids), ("location_dest_id", "in", location_ids)]
        lines = self.env["stock.move.line"].search(domain, order="date, id")
        return lines.filtered(lambda line: bool(self._line_warehouse(line, warehouses)))

    def _build_xlsx(self, lines):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet("Historial")
        header = workbook.add_format({"bold": True, "font_color": "#FFFFFF", "bg_color": "#1F4E78", "border": 1})
        date_fmt = workbook.add_format({"num_format": "yyyy-mm-dd hh:mm", "border": 1})
        number_fmt = workbook.add_format({"num_format": "#,##0.0000", "border": 1})
        text_fmt = workbook.add_format({"border": 1})
        columns = ["Fecha", "Referencia", "Producto", "Desde", "A", "Cantidad", "Estado", "Usuario", "Proveedor"]
        for col, label in enumerate(columns):
            sheet.write(0, col, label, header)
        state_field = self.env["stock.move.line"]._fields["state"]
        state_labels = dict(state_field._description_selection(self.env))
        for row, line in enumerate(lines, start=1):
            values = [
                fields.Datetime.context_timestamp(self, line.date).replace(tzinfo=None) if line.date else None,
                line.reference or line.move_id.reference or line.move_id.origin or "",
                line.product_id.display_name or "",
                line.location_id.complete_name or line.location_id.display_name or "",
                line.location_dest_id.complete_name or line.location_dest_id.display_name or "",
                line.product_uom_id._compute_quantity(line.quantity, line.product_id.uom_id),
                state_labels.get(line.state, line.state or ""),
                line.ferreteria_report_user_id.name or "",
                line.ferreteria_supplier_id.display_name or "",
            ]
            sheet.write_datetime(row, 0, values[0], date_fmt) if values[0] else sheet.write_blank(row, 0, None, date_fmt)
            for col in range(1, 5):
                sheet.write(row, col, values[col], text_fmt)
            sheet.write_number(row, 5, values[5], number_fmt)
            for col in range(6, 9):
                sheet.write(row, col, values[col], text_fmt)
        sheet.freeze_panes(1, 0)
        sheet.autofilter(0, 0, max(len(lines), 1), len(columns) - 1)
        sheet.set_column(0, 0, 18)
        sheet.set_column(1, 1, 22)
        sheet.set_column(2, 4, 34)
        sheet.set_column(5, 5, 14)
        sheet.set_column(6, 8, 22)
        workbook.close()
        return output.getvalue()

    def action_export_xlsx(self):
        self.ensure_one()
        content = self._build_xlsx(self._get_lines())
        self.write({
            "file_data": base64.b64encode(content),
            "file_name": "historial_movimientos_inventario.xlsx",
        })
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{self._name}/{self.id}/file_data/{self.file_name}?download=true",
            "target": "self",
        }
