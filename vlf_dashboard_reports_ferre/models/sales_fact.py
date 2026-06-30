# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError


class VlfSalesOrderFact(models.Model):
    """Read-only operational sales fact.

    One row represents one operational movement:
    - a confirmed administrative sale order;
    - a paid/done/invoiced POS order;
    - a posted customer credit note linked to an administrative sale order.

    Customer invoices are deliberately not inserted as sales rows. This prevents
    a POS order and its invoice from being counted twice.
    """

    _name = 'vlf.sales.order.fact'
    _description = 'Hecho consolidado de ventas operativas'
    _auto = False
    _rec_name = 'document'
    _order = 'date desc, id desc'

    date = fields.Datetime(string='Fecha', readonly=True)
    company_id = fields.Many2one('res.company', string='Compañía', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', readonly=True)
    channel = fields.Selection([
        ('sale', 'Ventas'),
        ('pos', 'Punto de Venta'),
    ], string='Canal', readonly=True)
    movement_type = fields.Selection([
        ('sale', 'Venta'),
        ('refund', 'Devolución'),
    ], string='Movimiento', readonly=True)
    document = fields.Char(string='Documento', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Cliente', readonly=True)
    user_id = fields.Many2one('res.users', string='Vendedor/Cajero', readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Sucursal / Almacén', readonly=True)
    pos_config_id = fields.Many2one('pos.config', string='Punto de Venta', readonly=True)
    state = fields.Char(string='Estado', readonly=True)
    is_invoiced = fields.Boolean(string='Facturada', readonly=True)
    amount_gross = fields.Monetary(string='Venta bruta', currency_field='currency_id', readonly=True)
    amount_untaxed = fields.Monetary(string='Subtotal', currency_field='currency_id', readonly=True)
    amount_tax = fields.Monetary(string='Impuestos', currency_field='currency_id', readonly=True)
    amount_discount = fields.Monetary(string='Descuentos', currency_field='currency_id', readonly=True)
    amount_refund = fields.Monetary(string='Devoluciones', currency_field='currency_id', readonly=True)
    amount_net = fields.Monetary(string='Venta neta', currency_field='currency_id', readonly=True)
    source_model = fields.Char(string='Modelo origen', readonly=True)
    source_id = fields.Integer(string='ID origen', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW vlf_sales_order_fact AS (
                SELECT
                    (so.id::bigint * 10 + 1) AS id,
                    so.date_order AS date,
                    so.company_id,
                    company.currency_id,
                    'sale'::varchar AS channel,
                    CASE WHEN so.amount_total < 0 THEN 'refund' ELSE 'sale' END::varchar AS movement_type,
                    so.name::varchar AS document,
                    so.partner_id,
                    so.user_id,
                    so.warehouse_id,
                    NULL::integer AS pos_config_id,
                    so.state::varchar AS state,
                    (so.invoice_status = 'invoiced') AS is_invoiced,
                    CASE WHEN so.amount_total >= 0 THEN (so.amount_total + GREATEST(sale_discount.amount, 0.0)) / COALESCE(NULLIF(so.currency_rate, 0.0), 1.0) ELSE 0.0 END AS amount_gross,
                    CASE WHEN so.amount_total >= 0 THEN so.amount_untaxed / COALESCE(NULLIF(so.currency_rate, 0.0), 1.0) ELSE 0.0 END AS amount_untaxed,
                    CASE WHEN so.amount_total >= 0 THEN so.amount_tax / COALESCE(NULLIF(so.currency_rate, 0.0), 1.0) ELSE 0.0 END AS amount_tax,
                    CASE WHEN so.amount_total >= 0 THEN GREATEST(sale_discount.amount, 0.0) / COALESCE(NULLIF(so.currency_rate, 0.0), 1.0) ELSE 0.0 END AS amount_discount,
                    ABS(LEAST(so.amount_total, 0.0)) / COALESCE(NULLIF(so.currency_rate, 0.0), 1.0) AS amount_refund,
                    so.amount_total / COALESCE(NULLIF(so.currency_rate, 0.0), 1.0) AS amount_net,
                    'sale.order'::varchar AS source_model,
                    so.id AS source_id
                FROM sale_order so
                JOIN res_company company ON company.id = so.company_id
                LEFT JOIN LATERAL (
                    SELECT COALESCE(SUM(sol.price_unit * sol.product_uom_qty * sol.discount / 100.0), 0.0) AS amount
                    FROM sale_order_line sol
                    WHERE sol.order_id = so.id
                      AND sol.display_type IS NULL
                ) sale_discount ON TRUE
                WHERE so.state IN ('sale', 'done')

                UNION ALL

                SELECT
                    (po.id::bigint * 10 + 2) AS id,
                    po.date_order AS date,
                    po.company_id,
                    company.currency_id,
                    'pos'::varchar AS channel,
                    CASE WHEN po.amount_total < 0 THEN 'refund' ELSE 'sale' END::varchar AS movement_type,
                    COALESCE(NULLIF(po.name, ''), po.pos_reference)::varchar AS document,
                    po.partner_id,
                    po.user_id,
                    pc.warehouse_id,
                    po.config_id AS pos_config_id,
                    po.state::varchar AS state,
                    (po.account_move IS NOT NULL) AS is_invoiced,
                    CASE WHEN po.amount_total >= 0 THEN (po.amount_total + GREATEST(pos_discount.amount, 0.0)) / COALESCE(NULLIF(po.currency_rate, 0.0), 1.0) ELSE 0.0 END AS amount_gross,
                    CASE WHEN po.amount_total >= 0 THEN (po.amount_total - po.amount_tax) / COALESCE(NULLIF(po.currency_rate, 0.0), 1.0) ELSE 0.0 END AS amount_untaxed,
                    CASE WHEN po.amount_total >= 0 THEN po.amount_tax / COALESCE(NULLIF(po.currency_rate, 0.0), 1.0) ELSE 0.0 END AS amount_tax,
                    CASE WHEN po.amount_total >= 0 THEN GREATEST(pos_discount.amount, 0.0) / COALESCE(NULLIF(po.currency_rate, 0.0), 1.0) ELSE 0.0 END AS amount_discount,
                    ABS(LEAST(po.amount_total, 0.0)) / COALESCE(NULLIF(po.currency_rate, 0.0), 1.0) AS amount_refund,
                    po.amount_total / COALESCE(NULLIF(po.currency_rate, 0.0), 1.0) AS amount_net,
                    'pos.order'::varchar AS source_model,
                    po.id AS source_id
                FROM pos_order po
                JOIN pos_config pc ON pc.id = po.config_id
                JOIN res_company company ON company.id = po.company_id
                LEFT JOIN LATERAL (
                    SELECT COALESCE(SUM(pol.price_unit * pol.qty * pol.discount / 100.0), 0.0) AS amount
                    FROM pos_order_line pol
                    WHERE pol.order_id = po.id
                ) pos_discount ON TRUE
                WHERE po.state IN ('paid', 'done', 'invoiced')

                UNION ALL

                SELECT
                    (am.id::bigint * 10 + 3) AS id,
                    (COALESCE(am.invoice_date, am.date)::timestamp + interval '12 hours') AS date,
                    am.company_id,
                    company.currency_id,
                    'sale'::varchar AS channel,
                    'refund'::varchar AS movement_type,
                    am.name::varchar AS document,
                    am.partner_id,
                    am.invoice_user_id AS user_id,
                    sale_link.warehouse_id,
                    NULL::integer AS pos_config_id,
                    am.state::varchar AS state,
                    TRUE AS is_invoiced,
                    0.0::numeric AS amount_gross,
                    0.0::numeric AS amount_untaxed,
                    0.0::numeric AS amount_tax,
                    0.0::numeric AS amount_discount,
                    ABS(am.amount_total_signed) AS amount_refund,
                    -ABS(am.amount_total_signed) AS amount_net,
                    'account.move'::varchar AS source_model,
                    am.id AS source_id
                FROM account_move am
                JOIN res_company company ON company.id = am.company_id
                JOIN LATERAL (
                    SELECT MIN(so2.warehouse_id) AS warehouse_id
                    FROM account_move_line aml
                    JOIN sale_order_line_invoice_rel rel ON rel.invoice_line_id = aml.id
                    JOIN sale_order_line sol ON sol.id = rel.order_line_id
                    JOIN sale_order so2 ON so2.id = sol.order_id
                    WHERE aml.move_id = am.id
                ) sale_link ON sale_link.warehouse_id IS NOT NULL
                WHERE am.move_type = 'out_refund'
                  AND am.state = 'posted'
                  AND NOT EXISTS (
                      SELECT 1
                      FROM pos_order pos_origin
                      WHERE pos_origin.account_move = am.id
                  )
            )
        """)

    def action_open_source(self):
        self.ensure_one()
        if self.source_model not in ('sale.order', 'pos.order', 'account.move') or not self.source_id:
            raise UserError(_('No se encontró el documento de origen.'))
        record = self.env[self.source_model].browse(self.source_id).exists()
        if not record:
            raise UserError(_('El documento de origen ya no existe o no es accesible.'))
        return {
            'type': 'ir.actions.act_window',
            'name': self.document or _('Documento origen'),
            'res_model': self.source_model,
            'res_id': record.id,
            'views': [[False, 'form']],
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model_create_multi
    def create(self, vals_list):
        raise UserError(_('Este modelo es de consulta y no permite crear registros.'))

    def write(self, vals):
        raise UserError(_('Este modelo es de consulta y no permite editar registros.'))

    def unlink(self):
        raise UserError(_('Este modelo es de consulta y no permite eliminar registros.'))
