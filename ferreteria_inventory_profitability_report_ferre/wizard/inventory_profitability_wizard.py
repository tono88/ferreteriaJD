import base64
import io

import xlsxwriter

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class FerreteriaInventoryProfitabilityWizard(models.TransientModel):
    _name = "ferreteria.inventory.profitability.wizard"
    _description = "Existencias y Rentabilidad"

    warehouse_ids = fields.Many2many("stock.warehouse", string="Almacenes")
    location_ids = fields.Many2many("stock.location", string="Ubicaciones")
    product_ids = fields.Many2many("product.product", string="Productos")
    default_code = fields.Char(string="Referencia interna")
    category_ids = fields.Many2many("product.category", string="Categorías")
    include_zero = fields.Boolean(string="Incluir existencia cero")
    line_ids = fields.One2many(
        "ferreteria.inventory.profitability.wizard.line",
        "wizard_id",
        string="Resultados",
        readonly=True,
    )
    total_quantity = fields.Float(compute="_compute_totals", string="Existencia total")
    total_inventory_cost = fields.Monetary(
        compute="_compute_totals",
        currency_field="currency_id",
        string="Costo total conocido",
    )
    total_sale_value = fields.Monetary(
        compute="_compute_totals",
        currency_field="currency_id",
        string="Valor potencial de venta total",
    )
    known_cost_sale_value = fields.Monetary(
        compute="_compute_totals",
        currency_field="currency_id",
        string="Valor potencial con costo conocido",
    )
    total_potential_profit = fields.Monetary(
        compute="_compute_totals",
        currency_field="currency_id",
        string="Utilidad potencial conocida",
    )
    consolidated_margin = fields.Float(compute="_compute_totals", string="Margen consolidado %")
    cost_coverage_percent = fields.Float(
        compute="_compute_totals",
        string="Cobertura de costo por valor %",
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, readonly=True)
    file_data = fields.Binary(readonly=True)
    file_name = fields.Char(readonly=True)

    @api.depends(
        "line_ids.quantity",
        "line_ids.inventory_cost_total",
        "line_ids.sale_value_total",
        "line_ids.potential_profit",
        "line_ids.has_purchase_history",
    )
    def _compute_totals(self):
        for wizard in self:
            known_cost_lines = wizard.line_ids.filtered("has_purchase_history")
            wizard.total_quantity = sum(wizard.line_ids.mapped("quantity"))
            wizard.total_inventory_cost = sum(known_cost_lines.mapped("inventory_cost_total"))
            wizard.total_sale_value = sum(wizard.line_ids.mapped("sale_value_total"))
            wizard.known_cost_sale_value = sum(known_cost_lines.mapped("sale_value_total"))
            wizard.total_potential_profit = sum(known_cost_lines.mapped("potential_profit"))
            wizard.consolidated_margin = (
                wizard.total_potential_profit / wizard.known_cost_sale_value * 100.0
                if wizard.known_cost_sale_value
                else 0.0
            )
            wizard.cost_coverage_percent = (
                wizard.known_cost_sale_value / wizard.total_sale_value * 100.0
                if wizard.total_sale_value
                else 0.0
            )

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

    def _locations_by_warehouse(self, warehouses):
        result = {}
        allowed_locations = self.env["stock.location"]
        for warehouse in warehouses:
            locations = self.env["stock.location"].search([
                ("id", "child_of", warehouse.lot_stock_id.id),
                ("usage", "=", "internal"),
            ])
            result[warehouse.id] = locations
            allowed_locations |= locations
        if self.location_ids and self.location_ids - allowed_locations:
            raise AccessError(_("No puede consultar ubicaciones fuera de los almacenes autorizados."))
        if self.location_ids:
            for warehouse_id in result:
                result[warehouse_id] &= self.location_ids
        return result

    def _product_domain(self):
        domain = [("is_storable", "=", True)]
        if self.product_ids:
            domain.append(("id", "in", self.product_ids.ids))
        if self.default_code:
            domain.append(("default_code", "ilike", self.default_code.strip()))
        if self.category_ids:
            domain.append(("categ_id", "child_of", self.category_ids.ids))
        return domain

    def _latest_purchase_data(self, products):
        result = {}
        moves = self.env["stock.move"].sudo().search([
            ("company_id", "=", self.env.company.id),
            ("state", "=", "done"),
            ("location_id.usage", "=", "supplier"),
            ("purchase_line_id", "!=", False),
            ("product_id", "in", products.ids),
        ], order="date desc, id desc")
        for move in moves:
            product = move.product_id
            if product.id in result:
                continue
            purchase_line = move.purchase_line_id
            cost = purchase_line.product_uom._compute_price(purchase_line.price_unit, product.uom_id)
            receipt_date = fields.Date.to_date(move.date)
            if purchase_line.currency_id != self.env.company.currency_id:
                cost = purchase_line.currency_id._convert(
                    cost,
                    self.env.company.currency_id,
                    self.env.company,
                    receipt_date,
                )
            result[product.id] = {
                "supplier": purchase_line.order_id.partner_id,
                "receipt_date": receipt_date,
                "cost": cost,
                "move": move,
            }
        return result

    def _prepare_rows(self):
        self.ensure_one()
        warehouses = self._selected_warehouses()
        locations_by_warehouse = self._locations_by_warehouse(warehouses)
        products = self.env["product.product"].search(self._product_domain())
        purchase_data = self._latest_purchase_data(products)
        rows = []
        for warehouse in warehouses.sorted(lambda record: record.name):
            locations = locations_by_warehouse[warehouse.id]
            if not locations:
                continue
            quant_domain = [
                ("location_id", "in", locations.ids),
                ("product_id", "in", products.ids),
            ]
            grouped = self.env["stock.quant"]._read_group(
                quant_domain,
                ["product_id", "location_id"],
                ["quantity:sum"],
            )
            quantities = {(product.id, location.id): quantity for product, location, quantity in grouped}
            keys = set(quantities)
            if self.include_zero:
                keys |= {(product.id, location.id) for product in products for location in locations}
            for product_id, location_id in sorted(keys, key=lambda key: (self.env["stock.location"].browse(key[1]).complete_name, self.env["product.product"].browse(key[0]).display_name)):
                quantity = float(quantities.get((product_id, location_id), 0.0) or 0.0)
                if not self.include_zero and not quantity:
                    continue
                product = self.env["product.product"].browse(product_id)
                location = self.env["stock.location"].browse(location_id)
                purchase = purchase_data.get(product.id)
                sale_price = float(product.list_price or 0.0)
                last_cost = float(purchase["cost"]) if purchase else 0.0
                has_purchase = bool(purchase)
                unit_profit = sale_price - last_cost if has_purchase else 0.0
                margin = unit_profit / sale_price * 100.0 if has_purchase and sale_price else 0.0
                rows.append({
                    "reference": product.default_code or "",
                    "product_id": product.id,
                    "category_id": product.categ_id.id,
                    "warehouse_id": warehouse.id,
                    "location_id": location.id,
                    "quantity": quantity,
                    "uom_id": product.uom_id.id,
                    "last_supplier_id": purchase["supplier"].id if purchase else False,
                    "last_receipt_date": purchase["receipt_date"] if purchase else False,
                    "has_purchase_history": has_purchase,
                    "cost_status": _("Disponible") if has_purchase else _("No disponible"),
                    "last_purchase_cost": last_cost if has_purchase else 0.0,
                    "inventory_cost_total": quantity * last_cost if has_purchase else 0.0,
                    "sale_price": sale_price,
                    "unit_profit": unit_profit if has_purchase else 0.0,
                    "margin_percent": margin,
                    "sale_value_total": quantity * sale_price,
                    "potential_profit": quantity * unit_profit if has_purchase else 0.0,
                })
        return rows

    def action_compute(self):
        self.ensure_one()
        self.line_ids.unlink()
        rows = self._prepare_rows()
        self.env["ferreteria.inventory.profitability.wizard.line"].create([
            dict(row, wizard_id=self.id) for row in rows
        ])
        return {
            "type": "ir.actions.act_window",
            "name": _("Existencias y Rentabilidad"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def _build_xlsx(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet("Existencias y Rentabilidad")
        title = workbook.add_format({"bold": True, "font_size": 14, "font_color": "#1F2937"})
        header = workbook.add_format({"bold": True, "font_color": "#FFFFFF", "bg_color": "#1F4E78", "border": 1, "text_wrap": True})
        text_fmt = workbook.add_format({"border": 1})
        qty_fmt = workbook.add_format({"num_format": "#,##0.0000", "border": 1})
        cost_fmt = workbook.add_format({"num_format": 'Q#,##0.00000000', "border": 1})
        money_fmt = workbook.add_format({"num_format": 'Q#,##0.00', "border": 1})
        percent_fmt = workbook.add_format({"num_format": "0.00%", "border": 1})
        date_fmt = workbook.add_format({"num_format": "yyyy-mm-dd", "border": 1})
        total_fmt = workbook.add_format({"bold": True, "bg_color": "#D9EAF7", "border": 1})
        total_money_fmt = workbook.add_format({"bold": True, "bg_color": "#D9EAF7", "border": 1, "num_format": 'Q#,##0.00'})
        total_qty_fmt = workbook.add_format({"bold": True, "bg_color": "#D9EAF7", "border": 1, "num_format": "#,##0.0000"})
        total_percent_fmt = workbook.add_format({"bold": True, "bg_color": "#D9EAF7", "border": 1, "num_format": "0.00%"})
        columns = [
            "Referencia", "Producto", "Categoría", "Almacén", "Ubicación", "Existencia",
            "Unidad de medida", "Último proveedor", "Fecha última recepción",
            "Último costo unitario de compra", "Estado costo", "Costo total conocido",
            "Precio de venta", "Utilidad unitaria", "Margen %", "Valor potencial de venta",
            "Utilidad potencial conocida",
        ]
        sheet.write(0, 0, "Existencias y Rentabilidad", title)
        sheet.merge_range(
            1,
            0,
            1,
            10,
            "Costo: última recepción de proveedor terminada; Precio de venta: Precio 1. "
            "Margen consolidado: solo líneas con costo conocido.",
        )
        for col, label in enumerate(columns):
            sheet.write(3, col, label, header)
        for row_idx, line in enumerate(self.line_ids, start=4):
            text_values = [
                line.reference,
                line.product_id.display_name,
                line.category_id.complete_name,
                line.warehouse_id.name,
                line.location_id.complete_name,
            ]
            for col, value in enumerate(text_values):
                sheet.write(row_idx, col, value or "", text_fmt)
            sheet.write_number(row_idx, 5, line.quantity, qty_fmt)
            sheet.write(row_idx, 6, line.uom_id.name or "", text_fmt)
            sheet.write(row_idx, 7, line.last_supplier_id.display_name or "", text_fmt)
            if line.last_receipt_date:
                sheet.write_datetime(row_idx, 8, fields.Date.to_date(line.last_receipt_date), date_fmt)
            else:
                sheet.write_blank(row_idx, 8, None, date_fmt)
            if line.has_purchase_history:
                sheet.write_number(row_idx, 9, line.last_purchase_cost, cost_fmt)
            else:
                sheet.write_blank(row_idx, 9, None, cost_fmt)
            sheet.write(row_idx, 10, line.cost_status, text_fmt)
            sheet.write_number(row_idx, 11, line.inventory_cost_total, money_fmt) if line.has_purchase_history else sheet.write_blank(row_idx, 11, None, money_fmt)
            sheet.write_number(row_idx, 12, line.sale_price, money_fmt)
            sheet.write_number(row_idx, 13, line.unit_profit, money_fmt) if line.has_purchase_history else sheet.write_blank(row_idx, 13, None, money_fmt)
            sheet.write_number(row_idx, 14, line.margin_percent / 100.0, percent_fmt) if line.has_purchase_history and line.sale_price else sheet.write_blank(row_idx, 14, None, percent_fmt)
            sheet.write_number(row_idx, 15, line.sale_value_total, money_fmt)
            sheet.write_number(row_idx, 16, line.potential_profit, money_fmt) if line.has_purchase_history else sheet.write_blank(row_idx, 16, None, money_fmt)
        total_row = 4 + len(self.line_ids)
        sheet.write(total_row, 0, "TOTALES", total_fmt)
        for col in range(1, len(columns)):
            sheet.write_blank(total_row, col, None, total_fmt)
        sheet.write_number(total_row, 5, self.total_quantity, total_qty_fmt)
        sheet.write_number(total_row, 11, self.total_inventory_cost, total_money_fmt)
        sheet.write_number(total_row, 14, self.consolidated_margin / 100.0, total_percent_fmt)
        sheet.write_number(total_row, 15, self.total_sale_value, total_money_fmt)
        sheet.write_number(total_row, 16, self.total_potential_profit, total_money_fmt)
        summary_row = total_row + 2
        sheet.merge_range(summary_row, 0, summary_row, 2, "Valor potencial con costo conocido", total_fmt)
        sheet.write_number(summary_row, 3, self.known_cost_sale_value, total_money_fmt)
        sheet.merge_range(summary_row + 1, 0, summary_row + 1, 2, "Cobertura de costo por valor", total_fmt)
        sheet.write_number(summary_row + 1, 3, self.cost_coverage_percent / 100.0, total_percent_fmt)
        sheet.merge_range(
            summary_row + 2,
            0,
            summary_row + 2,
            6,
            "La cobertura compara el valor potencial de las líneas con costo conocido contra el valor potencial total.",
            text_fmt,
        )
        sheet.freeze_panes(4, 0)
        sheet.autofilter(3, 0, max(total_row - 1, 3), len(columns) - 1)
        widths = [14, 34, 25, 18, 32, 14, 18, 28, 18, 23, 16, 20, 16, 18, 12, 20, 18]
        for col, width in enumerate(widths):
            sheet.set_column(col, col, width)
        workbook.close()
        return output.getvalue()

    def action_export_xlsx(self):
        self.ensure_one()
        if not self.line_ids:
            self.action_compute()
        content = self._build_xlsx()
        self.write({
            "file_data": base64.b64encode(content),
            "file_name": "existencias_y_rentabilidad.xlsx",
        })
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{self._name}/{self.id}/file_data/{self.file_name}?download=true",
            "target": "self",
        }


class FerreteriaInventoryProfitabilityWizardLine(models.TransientModel):
    _name = "ferreteria.inventory.profitability.wizard.line"
    _description = "Línea de Existencias y Rentabilidad"
    _order = "warehouse_id, location_id, product_id"

    wizard_id = fields.Many2one("ferreteria.inventory.profitability.wizard", required=True, ondelete="cascade")
    reference = fields.Char(string="Referencia")
    product_id = fields.Many2one("product.product", string="Producto", readonly=True)
    category_id = fields.Many2one("product.category", string="Categoría", readonly=True)
    warehouse_id = fields.Many2one("stock.warehouse", string="Almacén", readonly=True)
    location_id = fields.Many2one("stock.location", string="Ubicación", readonly=True)
    quantity = fields.Float(string="Existencia", digits="Product Unit of Measure", readonly=True)
    uom_id = fields.Many2one("uom.uom", string="UDM", readonly=True)
    last_supplier_id = fields.Many2one("res.partner", string="Último proveedor", readonly=True)
    last_receipt_date = fields.Date(string="Fecha última recepción", readonly=True)
    has_purchase_history = fields.Boolean(readonly=True)
    cost_status = fields.Char(string="Estado costo", readonly=True)
    last_purchase_cost = fields.Float(string="Último costo compra", digits=(16, 8), readonly=True)
    inventory_cost_total = fields.Monetary(string="Costo total conocido", currency_field="currency_id", readonly=True)
    sale_price = fields.Monetary(string="Precio venta", currency_field="currency_id", readonly=True)
    unit_profit = fields.Monetary(string="Utilidad unitaria", currency_field="currency_id", readonly=True)
    margin_percent = fields.Float(string="Margen %", digits=(16, 4), readonly=True)
    sale_value_total = fields.Monetary(string="Valor potencial venta", currency_field="currency_id", readonly=True)
    potential_profit = fields.Monetary(string="Utilidad potencial conocida", currency_field="currency_id", readonly=True)
    currency_id = fields.Many2one(related="wizard_id.currency_id", readonly=True)
