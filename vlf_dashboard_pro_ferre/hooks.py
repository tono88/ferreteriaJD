# -*- coding: utf-8 -*-

def post_init_hook(env):
    """Create practical predefined dashboards after install.

    The hook searches models/fields dynamically so the module is more tolerant to
    minor differences between Odoo 18 Community/Enterprise installations.
    """
    Dashboard = env['vlf.dashboard'].sudo()
    Item = env['vlf.dashboard.item'].sudo()
    IrModel = env['ir.model'].sudo()
    IrField = env['ir.model.fields'].sudo()
    currency = env.company.currency_id

    def model(model_name):
        return IrModel.search([('model', '=', model_name)], limit=1)

    def field(m, name):
        return IrField.search([('model_id', '=', m.id), ('name', '=', name)], limit=1) if m else False

    def dashboard(name, **extra):
        existing = Dashboard.search([('name', '=', name)], limit=1)
        if existing:
            return existing
        vals = {
            'name': name,
            'description': extra.pop('description', ''),
            'theme': extra.pop('theme', 'light'),
            'layout_mode': extra.pop('layout_mode', 'grid'),
            'color_palette': extra.pop('color_palette', 'business'),
            'auto_refresh': extra.pop('auto_refresh', False),
            'auto_refresh_seconds': extra.pop('auto_refresh_seconds', 60),
            'enable_realtime': extra.pop('enable_realtime', False),
            'enable_advanced_filters': True,
            'is_predefined': True,
        }
        vals.update(extra)
        return Dashboard.create(vals)

    def item(dash, name, item_type, model_name=False, measure=False, groupby=False, date_field=False, domain='[]', **kw):
        if Item.search([('dashboard_id', '=', dash.id), ('name', '=', name)], limit=1):
            return
        m = model(model_name) if model_name else False
        vals = {
            'dashboard_id': dash.id,
            'name': name,
            'item_type': item_type,
            'sequence': kw.pop('sequence', 10),
            'width': kw.pop('width', '1'),
            'height': kw.pop('height', 'medium'),
            'model_id': m.id if m else False,
            'domain': domain,
            'aggregation': kw.pop('aggregation', 'sum'),
            'limit': kw.pop('limit', 12),
            'sort_by': kw.pop('sort_by', 'value'),
            'sort_direction': kw.pop('sort_direction', 'desc'),
            'groupby_interval': kw.pop('groupby_interval', 'month'),
            'cumulative': kw.pop('cumulative', False),
            'target_value': kw.pop('target_value', 0.0),
            'target_label': kw.pop('target_label', 'Meta'),
            'show_target': kw.pop('show_target', True),
            'show_values': kw.pop('show_values', True),
            'show_legend': kw.pop('show_legend', True),
            'show_total': kw.pop('show_total', True),
            'unit_prefix': kw.pop('unit_prefix', ''),
            'unit_suffix': kw.pop('unit_suffix', ''),
            'currency_id': currency.id if kw.pop('use_currency', False) and currency else False,
            'number_system': kw.pop('number_system', 'compact'),
            'precision_digits': kw.pop('precision_digits', 2),
            'list_style': kw.pop('list_style', 'table'),
            'icon': kw.pop('icon', 'fa-bar-chart'),
            'help_text': kw.pop('help_text', ''),
            'color_palette': kw.pop('color_palette', 'inherit'),
        }
        if m:
            vals['measure_field_id'] = field(m, measure).id if measure and field(m, measure) else False
            vals['groupby_field_id'] = field(m, groupby).id if groupby and field(m, groupby) else False
            vals['date_field_id'] = field(m, date_field).id if date_field and field(m, date_field) else False
            list_names = kw.pop('list_fields', [])
            list_fields = [field(m, f).id for f in list_names if field(m, f)]
            if list_fields:
                vals['list_field_ids'] = [(6, 0, list_fields)]
        vals.update(kw)
        Item.create(vals)

    # Dashboard 1: Ejecutivo
    d_exec = dashboard(
        'Ejecutivo Gerencial',
        description='KPIs de alto nivel para ventas, POS, facturación, cartera e inventario.',
        theme='blue',
        auto_refresh=True,
        auto_refresh_seconds=90,
        enable_realtime=True,
    )
    item(d_exec, 'Ventas confirmadas', 'tile', 'sale.order', 'amount_total', False, 'date_order', "[('state','in',['sale','done'])]", sequence=1, width='1', use_currency=True, target_value=100000, icon='fa-line-chart')
    item(d_exec, 'Cotizaciones abiertas', 'tile', 'sale.order', False, False, 'date_order', "[('state','in',['draft','sent'])]", aggregation='count', sequence=2, width='1', icon='fa-file-text-o')
    item(d_exec, 'Facturación clientes', 'tile', 'account.move', 'amount_total_signed', False, 'invoice_date', "[('move_type','in',['out_invoice','out_refund']),('state','=','posted')]", sequence=3, width='1', use_currency=True, target_value=150000, icon='fa-money')
    item(d_exec, 'Ventas POS', 'tile', 'pos.order', 'amount_total', False, 'date_order', "[('state','in',['paid','done','invoiced'])]", sequence=4, width='1', use_currency=True, icon='fa-shopping-cart')
    item(d_exec, 'Ventas mensuales', 'area', 'sale.order', 'amount_total', 'date_order', 'date_order', "[('state','in',['sale','done'])]", sequence=5, width='2', cumulative=True, use_currency=True)
    item(d_exec, 'Facturación por estado de pago', 'doughnut', 'account.move', 'amount_total_signed', 'payment_state', 'invoice_date', "[('move_type','=','out_invoice'),('state','=','posted')]", sequence=6, width='1', use_currency=True)
    item(d_exec, 'Inventario por ubicación', 'horizontal_bar', 'stock.quant', 'quantity', 'location_id', False, "[]", sequence=7, width='1')
    item(d_exec, 'Pendientes gerenciales', 'todo', False, False, False, False, '[]', sequence=8, width='2', height='small', icon='fa-check-square-o')

    # Dashboard 2: Galería con todos los tipos de gráficas solicitados.
    d_gallery = dashboard(
        'Galería de Gráficas',
        description='Ejemplos funcionales de todos los tipos visuales incluidos, sin IA.',
        theme='purple',
        color_palette='contrast',
        layout_mode='grid',
    )
    item(d_gallery, 'Tile KPI', 'tile', 'sale.order', 'amount_total', False, 'date_order', "[('state','in',['sale','done'])]", sequence=1, use_currency=True, target_value=100000)
    item(d_gallery, 'Line Chart', 'line', 'sale.order', 'amount_total', 'date_order', 'date_order', "[('state','in',['sale','done'])]", sequence=2, width='2', use_currency=True)
    item(d_gallery, 'List View', 'list', 'sale.order', False, False, 'date_order', "[]", sequence=3, width='2', aggregation='count', list_fields=['name', 'partner_id', 'date_order', 'state', 'amount_total'])
    item(d_gallery, 'Bar Chart', 'bar', 'sale.order', 'amount_total', 'user_id', 'date_order', "[('state','in',['sale','done'])]", sequence=4, width='2', use_currency=True)
    item(d_gallery, 'Horizontal Bar Chart', 'horizontal_bar', 'sale.order', 'amount_total', 'partner_id', 'date_order', "[('state','in',['sale','done'])]", sequence=5, width='2', use_currency=True)
    item(d_gallery, 'To-do Item', 'todo', False, False, False, False, '[]', sequence=6, width='2')
    item(d_gallery, 'Polar Area Chart', 'polar_area', 'sale.order', False, 'state', 'date_order', "[]", sequence=7, aggregation='count')
    item(d_gallery, 'Pie Chart', 'pie', 'sale.order', False, 'state', 'date_order', "[]", sequence=8, aggregation='count')
    item(d_gallery, 'Doughnut Chart', 'doughnut', 'account.move', 'amount_total_signed', 'payment_state', 'invoice_date', "[('move_type','=','out_invoice'),('state','=','posted')]", sequence=9, use_currency=True)
    item(d_gallery, 'Flower Chart', 'flower', 'sale.order', 'amount_total', 'user_id', 'date_order', "[('state','in',['sale','done'])]", sequence=10, use_currency=True)
    item(d_gallery, 'Funnel Chart', 'funnel', 'sale.order', False, 'state', 'date_order', "[]", sequence=11, width='2', aggregation='count')
    item(d_gallery, 'Radial Chart', 'radial', 'sale.order', 'amount_total', False, 'date_order', "[('state','in',['sale','done'])]", sequence=12, target_value=100000, use_currency=True)
    item(d_gallery, 'Bullet Chart', 'bullet', 'sale.order', 'amount_total', False, 'date_order', "[('state','in',['sale','done'])]", sequence=13, target_value=100000, use_currency=True)
    item(d_gallery, 'Scatter Chart', 'scatter', 'sale.order', 'amount_total', 'date_order', 'date_order', "[('state','in',['sale','done'])]", sequence=14, width='2', use_currency=True)
    item(d_gallery, 'Radar Chart', 'radar', 'sale.order', 'amount_total', 'user_id', 'date_order', "[('state','in',['sale','done'])]", sequence=15, use_currency=True)
    item(d_gallery, 'Map View', 'map', 'res.partner', False, False, False, "[('partner_latitude','!=',False),('partner_longitude','!=',False)]", sequence=16, width='2')
    item(d_gallery, 'Area Chart', 'area', 'sale.order', 'amount_total', 'date_order', 'date_order', "[('state','in',['sale','done'])]", sequence=17, width='2', cumulative=True, use_currency=True)

    # Dashboard 3: Ventas
    d_sales = dashboard('Ventas', description='Seguimiento comercial por mes, vendedor, cliente y estado.', theme='green')
    item(d_sales, 'Ventas por mes', 'line', 'sale.order', 'amount_total', 'date_order', 'date_order', "[('state','in',['sale','done'])]", sequence=1, width='2', use_currency=True)
    item(d_sales, 'Ventas por vendedor', 'bar', 'sale.order', 'amount_total', 'user_id', 'date_order', "[('state','in',['sale','done'])]", sequence=2, width='2', use_currency=True)
    item(d_sales, 'Top clientes', 'horizontal_bar', 'sale.order', 'amount_total', 'partner_id', 'date_order', "[('state','in',['sale','done'])]", sequence=3, width='2', use_currency=True)
    item(d_sales, 'Embudo por estado', 'funnel', 'sale.order', False, 'state', 'date_order', "[]", sequence=4, width='2', aggregation='count')
    item(d_sales, 'Pedidos recientes', 'list', 'sale.order', False, False, 'date_order', "[]", sequence=5, width='4', aggregation='count', list_fields=['name', 'partner_id', 'user_id', 'date_order', 'state', 'amount_total'])

    # Dashboard 4: POS
    d_pos = dashboard('Punto de Venta', description='Indicadores para caja, sesiones, cajeros y estados POS.', theme='orange')
    item(d_pos, 'Ventas POS por día', 'area', 'pos.order', 'amount_total', 'date_order', 'date_order', "[('state','in',['paid','done','invoiced'])]", sequence=1, width='2', groupby_interval='day', use_currency=True)
    item(d_pos, 'Ventas por cajero', 'bar', 'pos.order', 'amount_total', 'user_id', 'date_order', "[('state','in',['paid','done','invoiced'])]", sequence=2, width='2', use_currency=True)
    item(d_pos, 'Órdenes por estado', 'pie', 'pos.order', False, 'state', 'date_order', "[]", sequence=3, aggregation='count')
    item(d_pos, 'Sesiones POS', 'horizontal_bar', 'pos.order', 'amount_total', 'session_id', 'date_order', "[('state','in',['paid','done','invoiced'])]", sequence=4, width='2', use_currency=True)
    item(d_pos, 'Órdenes POS recientes', 'list', 'pos.order', False, False, 'date_order', "[]", sequence=5, width='4', aggregation='count', list_fields=['name', 'session_id', 'user_id', 'date_order', 'state', 'amount_total'])

    # Dashboard 5: Contabilidad
    d_acc = dashboard('Contabilidad y Facturación', description='Facturas, saldos, estados de pago y documentos contables.', theme='blue')
    item(d_acc, 'Facturación mensual', 'area', 'account.move', 'amount_total_signed', 'invoice_date', 'invoice_date', "[('move_type','=','out_invoice'),('state','=','posted')]", sequence=1, width='2', use_currency=True)
    item(d_acc, 'Saldo por cliente', 'horizontal_bar', 'account.move', 'amount_residual_signed', 'partner_id', 'invoice_date', "[('move_type','=','out_invoice'),('state','=','posted')]", sequence=2, width='2', use_currency=True)
    item(d_acc, 'Estados de pago', 'doughnut', 'account.move', False, 'payment_state', 'invoice_date', "[('move_type','=','out_invoice'),('state','=','posted')]", sequence=3, aggregation='count')
    item(d_acc, 'Tipo de documento', 'polar_area', 'account.move', False, 'move_type', 'invoice_date', "[('state','=','posted')]", sequence=4, aggregation='count')
    item(d_acc, 'Facturas recientes', 'list', 'account.move', False, False, 'invoice_date', "[('move_type','in',['out_invoice','out_refund','in_invoice','in_refund'])]", sequence=5, width='4', aggregation='count', list_fields=['name', 'partner_id', 'invoice_date', 'move_type', 'payment_state', 'amount_total_signed'])

    # Dashboard 6: Inventario
    d_stock = dashboard('Inventario', description='Disponibilidad, reservas, ubicaciones e inventario negativo.', theme='green')
    item(d_stock, 'Inventario por producto', 'horizontal_bar', 'stock.quant', 'quantity', 'product_id', False, "[]", sequence=1, width='2')
    item(d_stock, 'Inventario por ubicación', 'bar', 'stock.quant', 'quantity', 'location_id', False, "[]", sequence=2, width='2')
    item(d_stock, 'Reservado por ubicación', 'area', 'stock.quant', 'reserved_quantity', 'location_id', False, "[]", sequence=3, width='2')
    item(d_stock, 'Negativos', 'list', 'stock.quant', False, False, False, "[('quantity','<',0)]", sequence=4, width='2', aggregation='count', list_fields=['product_id', 'location_id', 'quantity', 'reserved_quantity', 'company_id'])

    # To-do examples
    Todo = env['vlf.dashboard.todo'].sudo()
    if not Todo.search([('dashboard_id', '=', d_gallery.id)], limit=1):
        Todo.create([
            {'dashboard_id': d_gallery.id, 'name': 'Validar indicadores con gerencia', 'priority': '1', 'user_id': env.user.id},
            {'dashboard_id': d_gallery.id, 'name': 'Configurar metas comerciales', 'priority': '2', 'user_id': env.user.id},
            {'dashboard_id': d_exec.id, 'name': 'Revisar cartera vencida semanal', 'priority': '1', 'user_id': env.user.id},
        ])
