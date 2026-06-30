# -*- coding: utf-8 -*-
from collections import defaultdict
from datetime import datetime, timedelta

import pytz

from odoo import fields, _


class VlfDashboardMetricService:
    """Servicio Python puro para calcular métricas del dashboard.

    No es un modelo ORM: solo recibe un ``env`` de Odoo y ejecuta consultas
    sobre modelos reales. Esto evita registrar un modelo técnico sin tabla.
    """

    def __init__(self, env):
        self.env = env

    SALE_STATES = ('sale', 'done')
    POS_STATES = ('paid', 'done', 'invoiced')

    # -------------------------------------------------------------------------
    # Domain helpers
    # -------------------------------------------------------------------------
    def _date_bounds(self, filters, date_only=False):
        date_from = (filters or {}).get('date_from') or False
        date_to = (filters or {}).get('date_to') or False
        try:
            parsed_from = datetime.strptime(str(date_from), '%Y-%m-%d') if date_from else False
            parsed_to = datetime.strptime(str(date_to), '%Y-%m-%d') + timedelta(days=1) if date_to else False
        except (TypeError, ValueError):
            return False, False

        if date_only:
            return (
                parsed_from.strftime('%Y-%m-%d') if parsed_from else False,
                parsed_to.strftime('%Y-%m-%d') if parsed_to else False,
            )

        timezone_name = self.env.context.get('tz') or self.env.user.tz or 'UTC'
        try:
            timezone = pytz.timezone(timezone_name)
        except pytz.UnknownTimeZoneError:
            timezone = pytz.UTC

        def to_utc_string(value):
            if not value:
                return False
            localized = timezone.localize(value)
            utc_value = localized.astimezone(pytz.UTC).replace(tzinfo=None)
            return fields.Datetime.to_string(utc_value)

        return to_utc_string(parsed_from), to_utc_string(parsed_to)

    def _custom(self, filters, key):
        return ((filters or {}).get('custom') or {}).get(key) or False

    def _append_many2one_filter(self, domain, field_name, raw_value, model_name):
        if raw_value in (None, '', False):
            return
        try:
            domain.append((field_name, '=', int(raw_value)))
            return
        except (TypeError, ValueError):
            pass
        record_ids = self.env[model_name].search([('name', 'ilike', str(raw_value))]).ids
        domain.append((field_name, 'in', record_ids or [0]))

    def _fact_domain(self, filters=None, channel=None, movement_type=None):
        filters = filters or {}
        domain = [('company_id', '=', self.env.company.id)]
        date_from, date_to_exclusive = self._date_bounds(filters)
        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to_exclusive:
            domain.append(('date', '<', date_to_exclusive))
        selected_channel = channel or self._custom(filters, 'canal')
        if selected_channel in ('sale', 'pos'):
            domain.append(('channel', '=', selected_channel))
        if movement_type:
            domain.append(('movement_type', '=', movement_type))
        for key, field_name in (('sucursal', 'warehouse_id'), ('pos', 'pos_config_id')):
            value = self._custom(filters, key)
            if value:
                try:
                    domain.append((field_name, '=', int(value)))
                except (TypeError, ValueError):
                    domain.append(('id', '=', 0))
        self._append_many2one_filter(domain, 'partner_id', self._custom(filters, 'cliente'), 'res.partner')
        self._append_many2one_filter(domain, 'user_id', self._custom(filters, 'vendedor'), 'res.users')
        return domain

    def _pos_domain(self, filters=None, date_field='date_order'):
        filters = filters or {}
        domain = [
            ('company_id', '=', self.env.company.id),
            ('state', 'in', self.POS_STATES),
        ]
        date_from, date_to_exclusive = self._date_bounds(filters)
        if date_from:
            domain.append((date_field, '>=', date_from))
        if date_to_exclusive:
            domain.append((date_field, '<', date_to_exclusive))
        for key, field_name in (('sucursal', 'config_id.warehouse_id'), ('pos', 'config_id')):
            value = self._custom(filters, key)
            if value:
                try:
                    domain.append((field_name, '=', int(value)))
                except (TypeError, ValueError):
                    domain.append(('id', '=', 0))
        self._append_many2one_filter(domain, 'partner_id', self._custom(filters, 'cliente'), 'res.partner')
        self._append_many2one_filter(domain, 'user_id', self._custom(filters, 'vendedor'), 'res.users')
        return domain

    def _sale_line_domain(self, filters=None):
        filters = filters or {}
        domain = [
            ('order_id.company_id', '=', self.env.company.id),
            ('order_id.state', 'in', self.SALE_STATES),
            ('product_id', '!=', False),
        ]
        date_from, date_to_exclusive = self._date_bounds(filters)
        if date_from:
            domain.append(('order_id.date_order', '>=', date_from))
        if date_to_exclusive:
            domain.append(('order_id.date_order', '<', date_to_exclusive))
        warehouse = self._custom(filters, 'sucursal')
        if warehouse:
            try:
                domain.append(('order_id.warehouse_id', '=', int(warehouse)))
            except (TypeError, ValueError):
                domain.append(('id', '=', 0))
        self._append_many2one_filter(domain, 'order_id.partner_id', self._custom(filters, 'cliente'), 'res.partner')
        self._append_many2one_filter(domain, 'order_id.user_id', self._custom(filters, 'vendedor'), 'res.users')
        return domain

    def _pos_line_domain(self, filters=None):
        # Todos los filtros de _pos_domain pertenecen a pos.order. Al consultar
        # pos.order.line deben atravesar explícitamente order_id.
        domain = []
        for field_name, operator, value in self._pos_domain(filters):
            domain.append((f'order_id.{field_name}', operator, value))
        domain.append(('product_id', '!=', False))
        return domain

    def _currency_payload(self, value, drill_model='vlf.sales.order.fact'):
        value = float(value or 0.0)
        return {
            'labels': [_('Total')],
            'values': [value],
            'rows': [],
            'total': value,
            'currency': True,
            'drill_model': drill_model,
        }

    def _count_payload(self, value, drill_model='vlf.sales.order.fact'):
        value = int(value or 0)
        return {
            'labels': [_('Total')],
            'values': [value],
            'rows': [],
            'total': value,
            'currency': False,
            'drill_model': drill_model,
        }

    def _fact_sum(self, domain, field_name='amount_net'):
        groups = self.env['vlf.sales.order.fact'].read_group(domain, [f'{field_name}:sum'], [])
        return float(groups[0].get(field_name, 0.0) or 0.0) if groups else 0.0

    def _group_fact(self, domain, groupby, limit=12, boolean_labels=None):
        field_name = groupby.split(':', 1)[0]
        groups = self.env['vlf.sales.order.fact'].read_group(
            domain,
            ['amount_net:sum'],
            [groupby],
            orderby=f'{field_name} asc' if groupby.startswith('date:') else False,
            lazy=False,
        )
        pairs = []
        grouped_field = self.env['vlf.sales.order.fact']._fields.get(field_name)
        selection_labels = {}
        if grouped_field and grouped_field.type == 'selection' and not callable(grouped_field.selection):
            selection_labels = dict(grouped_field.selection or [])
        for group in groups:
            raw = group.get(field_name)
            if raw is None:
                raw = group.get(groupby)
            if boolean_labels is not None and isinstance(raw, bool):
                label = boolean_labels[raw]
            elif isinstance(raw, (list, tuple)) and len(raw) > 1:
                label = raw[1]
            elif selection_labels and raw in selection_labels:
                label = selection_labels[raw]
            else:
                label = raw if raw not in (None, False, '') else _('Sin valor')
            pairs.append((str(label), float(group.get('amount_net', 0.0) or 0.0)))
        if groupby.startswith('date:'):
            # Mostrar los períodos más recientes, conservando el orden cronológico.
            selected = pairs[-limit:] if limit else pairs
        else:
            selected = sorted(pairs, key=lambda pair: pair[1], reverse=True)[:limit]
        return {
            'labels': [pair[0] for pair in selected],
            'values': [pair[1] for pair in selected],
            'rows': [],
            'total': self._fact_sum(domain),
            'currency': True,
            'drill_model': 'vlf.sales.order.fact',
        }

    # -------------------------------------------------------------------------
    # Product metrics
    # -------------------------------------------------------------------------
    def _top_products(self, filters=None, channel=None, limit=10):
        filters = filters or {}
        totals = defaultdict(float)
        labels = {}
        requested_channel = channel or self._custom(filters, 'canal')
        selected_pos = self._custom(filters, 'pos')
        if selected_pos:
            if requested_channel == 'sale':
                return {'labels': [], 'values': [], 'rows': [], 'total': 0, 'currency': False, 'drill_model': 'vlf.sales.order.fact'}
            requested_channel = 'pos'

        if requested_channel in (False, 'sale'):
            sale_groups = self.env['sale.order.line'].read_group(
                self._sale_line_domain(filters),
                ['product_uom_qty:sum'],
                ['product_id'],
                lazy=False,
            )
            for group in sale_groups:
                product = group.get('product_id')
                if product:
                    totals[product[0]] += float(group.get('product_uom_qty', 0.0) or 0.0)
                    labels[product[0]] = product[1]

            refund_domain = [
                ('move_id.company_id', '=', self.env.company.id),
                ('move_id.move_type', '=', 'out_refund'),
                ('move_id.state', '=', 'posted'),
                ('sale_line_ids', '!=', False),
                ('move_id.pos_order_ids', '=', False),
                ('product_id', '!=', False),
            ]
            date_from, date_to_exclusive = self._date_bounds(filters, date_only=True)
            if date_from:
                refund_domain.append(('move_id.invoice_date', '>=', date_from))
            if date_to_exclusive:
                # invoice_date es Date; el límite exclusivo funciona correctamente.
                refund_domain.append(('move_id.invoice_date', '<', date_to_exclusive))
            warehouse = self._custom(filters, 'sucursal')
            partner = self._custom(filters, 'cliente')
            seller = self._custom(filters, 'vendedor')
            if warehouse:
                refund_domain.append(('sale_line_ids.order_id.warehouse_id', '=', int(warehouse)))
            self._append_many2one_filter(refund_domain, 'move_id.partner_id', partner, 'res.partner')
            self._append_many2one_filter(refund_domain, 'move_id.invoice_user_id', seller, 'res.users')
            refund_groups = self.env['account.move.line'].read_group(
                refund_domain,
                ['quantity:sum'],
                ['product_id'],
                lazy=False,
            )
            for group in refund_groups:
                product = group.get('product_id')
                if product:
                    totals[product[0]] -= abs(float(group.get('quantity', 0.0) or 0.0))
                    labels[product[0]] = product[1]

        if requested_channel in (False, 'pos'):
            pos_groups = self.env['pos.order.line'].read_group(
                self._pos_line_domain(filters),
                ['qty:sum'],
                ['product_id'],
                lazy=False,
            )
            for group in pos_groups:
                product = group.get('product_id')
                if product:
                    totals[product[0]] += float(group.get('qty', 0.0) or 0.0)
                    labels[product[0]] = product[1]

        pairs = sorted(
            [(labels[product_id], qty) for product_id, qty in totals.items()],
            key=lambda pair: pair[1],
            reverse=True,
        )[:limit]
        return {
            'labels': [pair[0] for pair in pairs],
            'values': [pair[1] for pair in pairs],
            'rows': [],
            'total': sum(totals.values()),
            'currency': False,
            'drill_model': 'vlf.sales.order.fact',
        }

    def _recent_sales(self, filters=None, channel=None, limit=20):
        fact = self.env['vlf.sales.order.fact']
        domain = self._fact_domain(filters, channel=channel)
        rows = []
        channel_selection = dict(fact._fields['channel'].selection)
        for record in fact.search(domain, order='date desc, id desc', limit=limit):
            rows.append({
                _('Fecha'): fields.Datetime.to_string(record.date) if record.date else '',
                _('Canal'): channel_selection.get(record.channel, record.channel),
                _('Documento'): record.document or '',
                _('Sucursal'): record.warehouse_id.display_name or '',
                _('Cliente'): record.partner_id.display_name or _('Consumidor final'),
                _('Vendedor/Cajero'): record.user_id.name or '',
                _('Venta neta'): record.amount_net,
            })
        return {
            'labels': [],
            'values': [],
            'rows': rows,
            'total': fact.search_count(domain),
            'currency': False,
            'drill_model': 'vlf.sales.order.fact',
        }

    def _payment_domain(self, filters=None):
        filters = filters or {}
        domain = [
            ('company_id', '=', self.env.company.id),
            ('pos_order_id.state', 'in', self.POS_STATES),
        ]
        date_from, date_to_exclusive = self._date_bounds(filters)
        if date_from:
            domain.append(('payment_date', '>=', date_from))
        if date_to_exclusive:
            domain.append(('payment_date', '<', date_to_exclusive))
        for key, field_name in (('pos', 'pos_order_id.config_id'), ('sucursal', 'pos_order_id.config_id.warehouse_id')):
            value = self._custom(filters, key)
            if value:
                try:
                    domain.append((field_name, '=', int(value)))
                except (TypeError, ValueError):
                    domain.append(('id', '=', 0))
        self._append_many2one_filter(domain, 'pos_order_id.partner_id', self._custom(filters, 'cliente'), 'res.partner')
        self._append_many2one_filter(domain, 'pos_order_id.user_id', self._custom(filters, 'vendedor'), 'res.users')
        return domain

    def _session_domain(self, filters=None):
        filters = filters or {}
        domain = [('config_id.company_id', '=', self.env.company.id)]
        for key, field_name in (('pos', 'config_id'), ('sucursal', 'config_id.warehouse_id')):
            value = self._custom(filters, key)
            if value:
                try:
                    domain.append((field_name, '=', int(value)))
                except (TypeError, ValueError):
                    domain.append(('id', '=', 0))
        session_model = self.env['pos.session']
        if 'start_at' in session_model._fields:
            date_from, date_to_exclusive = self._date_bounds(filters)
            if date_from:
                domain.append(('start_at', '>=', date_from))
            if date_to_exclusive:
                domain.append(('start_at', '<', date_to_exclusive))
        return domain

    def _billing_domain(self, filters=None):
        filters = filters or {}
        domain = [
            ('company_id', '=', self.env.company.id),
            ('move_type', 'in', ('out_invoice', 'out_refund')),
            ('state', '=', 'posted'),
        ]
        date_from, date_to_exclusive = self._date_bounds(filters, date_only=True)
        if date_from:
            domain.append(('invoice_date', '>=', date_from))
        if date_to_exclusive:
            domain.append(('invoice_date', '<', date_to_exclusive))
        self._append_many2one_filter(domain, 'partner_id', self._custom(filters, 'cliente'), 'res.partner')
        self._append_many2one_filter(domain, 'invoice_user_id', self._custom(filters, 'vendedor'), 'res.users')
        return domain

    # -------------------------------------------------------------------------
    # Public dispatch
    # -------------------------------------------------------------------------
    def get_metric_payload(self, metric_key, filters=None, limit=12):
        filters = filters or {}
        fact = self.env['vlf.sales.order.fact']

        if metric_key == 'sales.total_net':
            domain = self._fact_domain(filters)
            return self._currency_payload(self._fact_sum(domain))
        if metric_key == 'sales.pos_net':
            domain = self._fact_domain(filters, channel='pos')
            return self._currency_payload(self._fact_sum(domain))
        if metric_key == 'sales.admin_net':
            domain = self._fact_domain(filters, channel='sale')
            return self._currency_payload(self._fact_sum(domain))
        if metric_key == 'sales.refunds':
            domain = self._fact_domain(filters, movement_type='refund')
            return self._currency_payload(self._fact_sum(domain, 'amount_refund'))
        if metric_key in ('sales.order_count', 'pos.order_count'):
            channel = 'pos' if metric_key.startswith('pos.') else None
            domain = self._fact_domain(filters, channel=channel, movement_type='sale')
            return self._count_payload(fact.search_count(domain))
        if metric_key in ('sales.average_ticket', 'pos.average_ticket'):
            channel = 'pos' if metric_key.startswith('pos.') else None
            domain = self._fact_domain(filters, channel=channel, movement_type='sale')
            count = fact.search_count(domain)
            sold_total = self._fact_sum(domain, 'amount_net')
            return self._currency_payload(sold_total / count if count else 0.0)
        if metric_key == 'pos.refunds':
            domain = self._fact_domain(filters, channel='pos', movement_type='refund')
            return self._currency_payload(self._fact_sum(domain, 'amount_refund'))
        if metric_key == 'sales.by_month':
            return self._group_fact(self._fact_domain(filters), 'date:month', limit=limit)
        if metric_key == 'sales.by_warehouse':
            return self._group_fact(self._fact_domain(filters), 'warehouse_id', limit=limit)
        if metric_key == 'sales.by_channel':
            return self._group_fact(self._fact_domain(filters), 'channel', limit=limit)
        if metric_key == 'sales.top_customers':
            return self._group_fact(self._fact_domain(filters), 'partner_id', limit=limit)
        if metric_key == 'sales.top_products':
            return self._top_products(filters=filters, limit=limit)
        if metric_key == 'sales.recent':
            return self._recent_sales(filters=filters, limit=limit)
        if metric_key == 'pos.recent':
            return self._recent_sales(filters=filters, channel='pos', limit=limit)

        if metric_key == 'pos.by_day':
            return self._group_fact(self._fact_domain(filters, channel='pos'), 'date:day', limit=limit)
        if metric_key == 'pos.by_config':
            return self._group_fact(self._fact_domain(filters, channel='pos'), 'pos_config_id', limit=limit)
        if metric_key == 'pos.by_cashier':
            return self._group_fact(self._fact_domain(filters, channel='pos'), 'user_id', limit=limit)
        if metric_key == 'pos.by_warehouse':
            return self._group_fact(self._fact_domain(filters, channel='pos'), 'warehouse_id', limit=limit)
        if metric_key == 'pos.top_customers':
            return self._group_fact(self._fact_domain(filters, channel='pos'), 'partner_id', limit=limit)
        if metric_key == 'pos.by_payment_method':
            totals = defaultdict(float)
            labels = {}
            payments = self.env['pos.payment'].search(self._payment_domain(filters))
            for payment in payments:
                method = payment.payment_method_id
                if not method:
                    continue
                rate = payment.pos_order_id.currency_rate or 1.0
                totals[method.id] += float(payment.amount or 0.0) / rate
                labels[method.id] = method.display_name
            all_pairs = [(labels[method_id], amount) for method_id, amount in totals.items()]
            global_total = sum(amount for _label, amount in all_pairs)
            pairs = sorted(all_pairs, key=lambda pair: pair[1], reverse=True)[:limit]
            return {
                'labels': [pair[0] for pair in pairs],
                'values': [pair[1] for pair in pairs],
                'rows': [],
                'total': global_total,
                'currency': True,
                'drill_model': 'pos.payment',
            }
        if metric_key == 'pos.invoicing_status':
            domain = self._fact_domain(filters, channel='pos')
            return self._group_fact(domain, 'is_invoiced', limit=2, boolean_labels={True: _('Facturadas'), False: _('No facturadas')})
        if metric_key == 'pos.top_products':
            return self._top_products(filters=filters, channel='pos', limit=limit)
        if metric_key == 'pos.sessions_state':
            domain = self._session_domain(filters)
            groups = self.env['pos.session'].read_group(domain, [], ['state'], lazy=False)
            labels = []
            values = []
            state_selection = dict(self.env['pos.session']._fields['state'].selection)
            for group in groups:
                state = group.get('state')
                labels.append(state_selection.get(state, state or _('Sin valor')))
                values.append(group.get('__count', 0))
            return {
                'labels': labels,
                'values': values,
                'rows': [],
                'total': sum(values),
                'currency': False,
                'drill_model': 'pos.session',
            }
        if metric_key == 'pos.discount_total':
            domain = self._fact_domain(filters, channel='pos', movement_type='sale')
            return self._currency_payload(self._fact_sum(domain, 'amount_discount'), drill_model='vlf.sales.order.fact')

        if metric_key == 'billing.issued':
            domain = self._billing_domain(filters)
            groups = self.env['account.move'].read_group(domain, ['amount_total_signed:sum'], [])
            value = groups[0].get('amount_total_signed', 0.0) if groups else 0.0
            return self._currency_payload(value, drill_model='account.move')


        return {
            'labels': [], 'values': [], 'rows': [], 'total': 0,
            'currency': False, 'drill_model': False,
        }

    def get_metric_action(self, metric_key, filters=None, item_name=None):
        filters = filters or {}
        if metric_key == 'billing.issued':
            domain = self._billing_domain(filters)
            model = 'account.move'
        elif metric_key == 'pos.by_payment_method':
            domain = self._payment_domain(filters)
            model = 'pos.payment'
        elif metric_key == 'pos.sessions_state':
            domain = self._session_domain(filters)
            model = 'pos.session'
        elif metric_key == 'pos.discount_total':
            domain = self._fact_domain(filters, channel='pos', movement_type='sale')
            model = 'vlf.sales.order.fact'
        else:
            if metric_key.startswith('pos.') or metric_key == 'sales.pos_net':
                channel = 'pos'
            elif metric_key == 'sales.admin_net':
                channel = 'sale'
            else:
                channel = None
            if metric_key in ('sales.refunds', 'pos.refunds'):
                movement_type = 'refund'
            elif metric_key in ('sales.order_count', 'sales.average_ticket', 'pos.order_count', 'pos.average_ticket'):
                movement_type = 'sale'
            else:
                movement_type = None
            domain = self._fact_domain(filters, channel=channel, movement_type=movement_type)
            model = 'vlf.sales.order.fact'
        return {
            'type': 'ir.actions.act_window',
            'name': item_name or _('Detalle de la métrica'),
            'res_model': model,
            'views': [[False, 'list'], [False, 'form']],
            'view_mode': 'list,form',
            'domain': domain,
            'target': 'current',
            'context': {'create': False},
        }
