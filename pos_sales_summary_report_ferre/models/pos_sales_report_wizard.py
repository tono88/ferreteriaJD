
# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import AccessError
from datetime import datetime, time
import pytz

REPORT_XMLID = "pos_sales_summary_report_ferre.action_report_pos_sales_summary"
REPORT_NAME = "pos_sales_summary_report_ferre.report_pos_sales_summary"
REPORT_XLSX_XMLID = "pos_sales_summary_report_ferre.action_report_pos_sales_summary_xlsx"  # 👈 NUEVO

class PosSalesReportWizard(models.TransientModel):
    _name = "pos.sales.report.wizard"
    _description = "Asistente de Reporte de Ventas POS (rango fechas)"

    pos_config_id = fields.Many2one(
        "pos.config",
        string="Punto de venta",
        help="Si no seleccionas nada, se incluyen todos los puntos de venta."
    )
    # A reporting-only selector. Do NOT expose pos.config through normal
    # record rules: operational POS access must remain scoped.
    global_pos_config_id = fields.Selection(
        selection="_selection_global_pos_configs",
        string="Punto de venta",
        help="Si no seleccionas nada, se incluyen todos los puntos de venta.",
    )
    can_select_global_pos = fields.Boolean(
        compute="_compute_can_select_global_pos",
    )

    @api.depends_context("uid")
    def _compute_can_select_global_pos(self):
        is_global_reader = self.env.user.has_group(
            "ferreteria_user_scope_ferre.group_pos_global_order_read"
        )
        for wizard in self:
            wizard.can_select_global_pos = is_global_reader

    @api.model
    def _global_pos_catalog(self):
        """Only names/IDs of active POS in *currently allowed* companies.

        This technical read grants no POS operation, session or write access.
        It is deliberately not callable as a cross-company catalog by normal
        scoped users. Validations on both wizard and report use this method.
        """
        if not self.env.user.has_group(
            "ferreteria_user_scope_ferre.group_pos_global_order_read"
        ):
            return {}
        company_ids = self.env.companies.ids
        if not company_ids:
            return {}
        records = self.env["pos.config"].sudo().search_read(
            [("company_id", "in", company_ids), ("active", "=", True)],
            fields=["id", "name"],
            order="name, id",
        )
        return {record["id"]: record["name"] for record in records}

    @api.model
    def _selection_global_pos_configs(self):
        return [
            (str(pos_id), name)
            for pos_id, name in self._global_pos_catalog().items()
        ]

    @api.model
    def _assert_report_pos_filter_allowed(self, pos_id):
        """Validate client-supplied POS IDs, including direct report RPCs."""
        if not pos_id:
            return
        try:
            pos_id = int(pos_id)
            if pos_id <= 0:
                raise ValueError("POS ID must be positive")
        except (TypeError, ValueError):
            raise AccessError(_("El punto de venta seleccionado no es válido."))

        if self.env.user.has_group(
            "ferreteria_user_scope_ferre.group_pos_global_order_read"
        ):
            if pos_id not in self._global_pos_catalog():
                raise AccessError(
                    _("No tiene autorización para filtrar por ese punto de venta.")
                )
        else:
            # No sudo: normal users retain their original pos.config rules.
            allowed = self.env["pos.config"].search(
                [
                    ("id", "=", pos_id),
                    ("company_id", "in", self.env.companies.ids),
                ],
                limit=1,
            )
            if not allowed:
                raise AccessError(
                    _("No tiene autorización para filtrar por ese punto de venta.")
                )

    def _selected_report_pos(self):
        """Return the existing report contract: (pos_config_id, name)."""
        self.ensure_one()
        if self.env.user.has_group(
            "ferreteria_user_scope_ferre.group_pos_global_order_read"
        ):
            if not self.global_pos_config_id:
                return False, "Todos"
            pos_id = int(self.global_pos_config_id)
            catalog = self._global_pos_catalog()
            if pos_id not in catalog:
                raise AccessError(
                    _("No tiene autorización para filtrar por ese punto de venta.")
                )
            return pos_id, catalog[pos_id]

        if not self.pos_config_id:
            return False, "Todos"
        self._assert_report_pos_filter_allowed(self.pos_config_id.id)
        return self.pos_config_id.id, self.pos_config_id.display_name

    partner_ids = fields.Many2many(
        "res.partner",
        string="Clientes",
        help="Si lo dejas vacio, se incluyen todos los clientes."
    )


    order_by_internal_correlative = fields.Boolean(
        string="Ordenar lineal por correlativo interno",
        help="Si esta marcado, el reporte se mostrara lineal, ordenado por el correlativo interno, sin agrupar por cliente."
    )

    date_from = fields.Date(string="Desde", required=True, default=lambda self: fields.Date.context_today(self))
    date_to = fields.Date(string="Hasta", required=True, default=lambda self: fields.Date.context_today(self))
    invoice_filter = fields.Selection([
        ("all", "Todos"),
        ("invoiced", "Solo Facturadas"),
        ("not_invoiced", "Solo NO Facturadas"),
    ], string="Facturación", required=True, default="all",
       help="Contado = pagos en efectivo. Crédito = otros métodos. El filtro limita qué órdenes se incluyen.")

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for w in self:
            if w.date_to and w.date_from and w.date_to < w.date_from:
                raise models.ValidationError(_("La fecha 'Hasta' no puede ser menor a 'Desde'."))

    def _get_utc_bounds(self):
        self.ensure_one()
        user_tz = pytz.timezone(self.env.user.tz or "UTC")
        start_local = datetime.combine(self.date_from, time.min)
        end_local = datetime.combine(self.date_to, time.max)
        start_utc = user_tz.localize(start_local).astimezone(pytz.utc)
        end_utc = user_tz.localize(end_local).astimezone(pytz.utc)
        return start_utc.strftime("%Y-%m-%d %H:%M:%S"), end_utc.strftime("%Y-%m-%d %H:%M:%S")

    def _fallback_report_action(self):
        report = self.env["ir.actions.report"].sudo().search([("report_name", "=", REPORT_NAME)], limit=1)
        if not report:
            raise models.ValidationError(
                _("No se encontro la accion de reporte %s. Verifique la configuracion en Ajustes / Tecnico / Acciones / Reportes.")
                % REPORT_NAME
            )
        return report


    def action_print_pdf(self):
        self.ensure_one()
        start_utc, end_utc = self._get_utc_bounds()
        pos_id, pos_name = self._selected_report_pos()
        data = {
            "date_from": str(self.date_from),
            "date_to": str(self.date_to),
            "invoice_filter": self.invoice_filter,
            "start_utc": start_utc,
            "end_utc": end_utc,
            # 👇 nuevo
            "pos_config_id": pos_id,
            "pos_config_name": pos_name,
            # 👇 NUEVO: filtro por clientes
            "partner_ids": self.partner_ids.ids,
            "partner_names": ", ".join(self.partner_ids.mapped("display_name")) if self.partner_ids else "Todos",
            # ?? NUEVO: flag de vista lineal por correlativo
            "order_by_internal_correlative": self.order_by_internal_correlative,

       }
        Report = self.env["ir.actions.report"].sudo()    
        report = self.env.ref(REPORT_XMLID, raise_if_not_found=False) or self._fallback_report_action()
        # 2) Si no existe, buscar por nombre de reporte
        if not report:
            report = Report.search([
                ("report_name", "=", "pos_sales_summary_report_ferre.report_pos_sales_summary"),
                ("report_type", "=", "pdf"),
                ("model", "=", "pos.order"),
            ], limit=1)

        # 3) Si tampoco existe, crearlo en caliente
        if not report:
            report = Report.create({
                "name": "Reporte de Ventas POS",
                "model": "pos.order",
                "report_type": "pdf",
                "report_name": "pos_sales_summary_report_ferre.report_pos_sales_summary",
                "report_file": "pos_sales_summary_report_ferre.report_pos_sales_summary",
            })
        
        
        return report.report_action(None, data=data)

    def action_print_xlsx(self):
        self.ensure_one()
        start_utc, end_utc = self._get_utc_bounds()
        pos_id, pos_name = self._selected_report_pos()
        data = {
            "date_from": str(self.date_from),
            "date_to": str(self.date_to),
            "invoice_filter": self.invoice_filter,
            "start_utc": start_utc,
            "end_utc": end_utc,
            "pos_config_id": pos_id,
            "pos_config_name": pos_name,
            # 👇 NUEVO: filtro por clientes
            "partner_ids": self.partner_ids.ids,
            "partner_names": ", ".join(self.partner_ids.mapped("display_name")) if self.partner_ids else "Todos",
            # ?? NUEVO: flag de vista lineal por correlativo
            "order_by_internal_correlative": self.order_by_internal_correlative,

        }
        Report = self.env["ir.actions.report"].sudo()

        # 1) Intentar por external id (si el XML sí se cargó)
        report = self.env.ref(REPORT_XLSX_XMLID, raise_if_not_found=False)

        # 2) Si no existe, buscar por nombre de reporte
        if not report:
            report = Report.search([
                ("report_name", "=", "pos_sales_summary_report_ferre.report_pos_sales_summary_xlsx"),
                ("report_type", "=", "xlsx"),
                ("model", "=", "pos.order"),
            ], limit=1)

        # 3) Si tampoco existe, crearlo en caliente
        if not report:
            report = Report.create({
                "name": "Reporte de Ventas POS (XLSX)",
                "model": "pos.order",
                "report_type": "xlsx",
                "report_name": "pos_sales_summary_report_ferre.report_pos_sales_summary_xlsx",
                "report_file": "pos_sales_summary_report_ferre.report_pos_sales_summary_xlsx",
            })
        return report.report_action(None, data=data)

