"""Diagnóstico de SOLO LECTURA para Odoo shell (COPIA_PRDO_CUIDADO).

USO: editar DATE_FROM y DATE_TO al mismo rango del reporte probado, y
 ejecutarlo dentro de odoo shell conectado EXCLUSIVAMENTE a COPIA_PRDO_CUIDADO.
No ejecuta create/write/unlink, no instala módulos, ni realiza commits.
"""
from datetime import datetime, time
from collections import defaultdict
import pytz

DATE_FROM = '2026-10-01'     # Ajustar a la fecha DESDE del wizard
DATE_TO = '2026-10-12'       # Ajustar a la fecha HASTA del wizard
USER_LOGIN = 'corpjb.atebelan@gmail.com'
POS_NAMES = ('JB Central', 'Taxisco', 'Palinche')

user = env['res.users'].sudo().search([('login', '=', USER_LOGIN)], limit=1)
if not user:
    raise ValueError('No se encontró el usuario Ana Lucía')
if not user.has_group('ferreteria_user_scope_ferre.group_pos_global_order_read'):
    raise ValueError('Ana no tiene el grupo de lectura global en esta base')

companies = user.company_ids.ids
if not companies:
    raise ValueError('Ana no tiene compañías autorizadas')
tz = pytz.timezone(user.tz or 'America/Guatemala')
start_utc = tz.localize(datetime.combine(datetime.fromisoformat(DATE_FROM).date(), time.min)).astimezone(pytz.utc)
end_utc = tz.localize(datetime.combine(datetime.fromisoformat(DATE_TO).date(), time.max)).astimezone(pytz.utc)
base_domain = [
    ('state', 'in', ['paid', 'done', 'invoiced']),
    ('date_order', '>=', start_utc.strftime('%Y-%m-%d %H:%M:%S')),
    ('date_order', '<=', end_utc.strftime('%Y-%m-%d %H:%M:%S')),
    ('company_id', 'in', companies),
]
user_orders = env["pos.order"].with_user(user).with_context(allowed_company_ids=companies)
print('BASE: COPIA_PRDO_CUIDADO — verificar identidad manualmente')
print('Usuario:', user.login, 'grupo global: SÍ', 'compañías:', companies)
print('Rango local:', DATE_FROM, DATE_TO)

for name in POS_NAMES:
    configs = env['pos.config'].sudo().search([
        ('name', '=', name), ('company_id', 'in', companies),
    ])
    if not configs:
        print(f'{name}: no hay POS con este nombre en compañías autorizadas')
        continue
    orders = user_orders.search(base_domain + [('config_id', 'in', configs.ids)], order='date_order desc', limit=5)
    if not orders:
        print(f'{name}: no se encontraron órdenes legibles en el rango')
        continue
    print(f'\n{name}: {len(orders)} órdenes de muestra (máximo 5)')
    for order in orders:
        try:
            user_visible = order.payment_ids
            normal_amounts = [p.amount for p in user_visible]
            normal_sum = sum(normal_amounts)
            normal_count = len(normal_amounts)
            normal_status = 'OK'
        except Exception as exc:
            normal_sum = None
            normal_count = None
            normal_status = type(exc).__name__
        technical_payments = env['pos.payment'].sudo().search([
            ('pos_order_id', '=', order.id),
            ('pos_order_id.company_id', 'in', companies),
        ])
        technical_sum = sum(technical_payments.mapped('amount'))
        print({
            'order_id': order.id,
            'order_name': order.name,
            'pos': name,
            'total_orden': order.amount_total,
            'pagos_usuario_n': normal_count,
            'pagos_usuario_suma': normal_sum,
            'acceso_usuario': normal_status,
            'pagos_tecnicos_n': len(technical_payments),
            'pagos_tecnicos_suma': technical_sum,
            'possible_omission': bool(technical_payments) and (normal_sum is None or abs(technical_sum - normal_sum) > 0.009),
        })
print('\nNO SE HICIERON MODIFICACIONES')
