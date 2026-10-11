# -*- coding: utf-8 -*-
"""Read-only historical on-hand stock for the predefined Inventario dashboard.

Uses the same past-date accounting principle as Odoo 18 product.qty_available:
current internal quants - validated incoming moves since cutoff + validated
outgoing moves since cutoff.  Uses stock.move.quantity with product_uom
conversion (not stock.move.line.quantity in a potentially different UoM).
No SQL, stock adjustments, or database writes are performed here.
"""
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone

import pytz

from odoo import _, fields
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero, float_round


GUATEMALA_TZ = pytz.timezone('America/Guatemala')


class InventoryHistoryService:
    def __init__(self, env):
        self.env = env

    def warehouses(self):
        # Respect regular record rules and the active company. In this project
        # branches are different stock.warehouse records in ONE company.
        return self.env['stock.warehouse'].with_context(active_test=False).search([
            ('company_id', '=', self.env.company.id),
        ], order='name, id')

    def warehouse_options(self):
        return [{'id': wh.id, 'name': wh.name, 'code': wh.code or ''} for wh in self.warehouses()]

    @staticmethod
    def cutoff_utc(date_text):
        if not isinstance(date_text, str):
            raise UserError(_('Seleccione una fecha de cierre válida (AAAA-MM-DD).'))
        try:
            selected = date.fromisoformat(date_text)
        except (ValueError, TypeError):
            raise UserError(_('La fecha de inventario debe tener el formato AAAA-MM-DD.'))
        today = datetime.now(GUATEMALA_TZ).date()
        if selected > today:
            raise UserError(_('No es posible consultar el cierre de una fecha futura.'))
        # Exclude next-day midnight, respecting Guatemala local time and UTC
        # storage of Odoo Datetime values.
        next_midnight = GUATEMALA_TZ.localize(datetime.combine(selected + timedelta(days=1), time.min))
        utc_naive = next_midnight.astimezone(timezone.utc).replace(tzinfo=None)
        return fields.Datetime.to_string(utc_naive), selected == today

    def _stock_locations(self, warehouses):
        roots = warehouses.mapped('view_location_id').ids
        if not roots:
            return self.env['stock.location'].browse(), {}
        locations = self.env['stock.location'].with_context(active_test=False).search([
            ('id', 'child_of', roots),
            ('usage', '=', 'internal'),
            ('company_id', 'in', [False, self.env.company.id]),
        ])
        warehouse_by_root = {wh.view_location_id.id: wh for wh in warehouses}
        location_warehouse = {}
        for location in locations:
            cursor = location
            visited = set()
            while cursor and cursor.id not in visited:
                visited.add(cursor.id)
                wh = warehouse_by_root.get(cursor.id)
                if wh:
                    location_warehouse[location.id] = wh.id
                    break
                cursor = cursor.location_id
        # Only physical locations demonstrably underneath a selected warehouse.
        locations = locations.filtered(lambda loc: loc.id in location_warehouse)
        return locations, location_warehouse

    def snapshot(self, date_text, warehouse_id=None):
        cutoff, provisional = self.cutoff_utc(date_text)
        warehouses = self.warehouses()
        if warehouse_id not in (None, False, ''):
            try:
                wh_id = int(warehouse_id)
            except (TypeError, ValueError):
                raise UserError(_('Almacén seleccionado no válido.'))
            warehouses = warehouses.filtered(lambda wh: wh.id == wh_id)
            if not warehouses:
                raise UserError(_('El almacén no está disponible para la compañía actual.'))
        locations, loc_to_wh = self._stock_locations(warehouses)
        warehouse_lookup = {wh.id: wh for wh in warehouses}
        if not locations:
            return {
                'quantities': {}, 'warehouses': warehouse_lookup, 'locations': {},
                'products': {}, 'warehouse_by_location': {}, 'provisional': provisional,
            }

        loc_ids = locations.ids
        balance = defaultdict(float)  # (product_id, location_id) -> qty in product UoM
        Quant = self.env['stock.quant'].with_context(active_test=False)
        for product, location, quantity in Quant._read_group([
            ('company_id', '=', self.env.company.id),
            ('location_id', 'in', loc_ids),
        ], ['product_id', 'location_id'], ['quantity:sum']):
            if product and location:
                balance[(product.id, location.id)] += quantity or 0.0

        # Odoo 18 core qty_available(to_date) reverses done stock.move
        # quantities after to_date, converting product_uom to the product UoM.
        # This is extended here with per-location grouping for warehouse charts.
        Move = self.env['stock.move'].with_context(active_test=False)
        for source, sign in (('location_id', 1.0), ('location_dest_id', -1.0)):
            domain = [
                ('company_id', '=', self.env.company.id),
                ('state', '=', 'done'),
                ('date', '>=', cutoff),
                (source, 'in', loc_ids),
            ]
            for product, uom, location, quantity in Move._read_group(
                domain, ['product_id', 'product_uom', source], ['quantity:sum']
            ):
                if not product or not uom or not location:
                    continue
                qty_product_uom = uom._compute_quantity(quantity or 0.0, product.uom_id, round=False)
                balance[(product.id, location.id)] += sign * qty_product_uom

        Product = self.env['product.product']
        product_ids = list({product_id for product_id, _ in balance})
        products = {prod.id: prod for prod in Product.browse(product_ids).exists()}
        location_lookup = {location.id: location for location in locations}
        clean = {}
        for (product_id, location_id), qty in balance.items():
            product = products.get(product_id)
            if not product:
                continue
            rounding = product.uom_id.rounding or 0.01
            if float_is_zero(qty, precision_rounding=rounding):
                continue
            clean[(product_id, location_id)] = float_round(qty, precision_rounding=rounding)

        return {
            'quantities': clean,
            'warehouses': warehouse_lookup,
            'locations': location_lookup,
            'products': products,
            'warehouse_by_location': loc_to_wh,
            'provisional': provisional,
        }

    @staticmethod
    def _pairs(item, mapping):
        pairs = item._sort_pairs(list(mapping.items()))
        return {
            'labels': [key for key, _ in pairs],
            'values': [round(value, 4) for _, value in pairs],
            'rows': [],
            'total': round(sum(mapping.values()), 4),
        }

    def item_data(self, item, snapshot):
        quantity = snapshot['quantities']
        products = snapshot['products']
        locations = snapshot['locations']
        if item.item_type == 'list' and item.name == 'Negativos':
            entries = [
                (qty, products[product_id].display_name, locations[loc_id].complete_name)
                for (product_id, loc_id), qty in quantity.items() if qty < 0
            ]
            entries.sort(key=lambda entry: (entry[0], entry[1], entry[2]))
            return {
                'labels': [], 'values': [],
                'rows': [
                    {'Producto': name, 'Ubicación': loc, 'Cantidad': round(qty, 4)}
                    for qty, name, loc in entries[:max(item.limit or 20, 1)]
                ],
                'total': len(entries),
            }
        if item.measure_field_id.name != 'quantity' or item.aggregation != 'sum':
            return None
        groupby = item.groupby_field_id.name if item.groupby_field_id else ''
        by_label = defaultdict(float)
        if groupby == 'product_id':
            for (product_id, _), qty in quantity.items():
                by_label[products[product_id].display_name] += qty
        elif groupby == 'location_id':
            for (_, location_id), qty in quantity.items():
                by_label[locations[location_id].complete_name] += qty
        else:
            return None
        return self._pairs(item, by_label)

    @staticmethod
    def warehouse_summary(snapshot):
        by_wh = defaultdict(float)
        products_by_wh = defaultdict(lambda: defaultdict(float))
        for (product_id, location_id), qty in snapshot['quantities'].items():
            wh_id = snapshot['warehouse_by_location'][location_id]
            by_wh[wh_id] += qty
            products_by_wh[wh_id][product_id] += qty
        return [
            {'id': wh_id, 'name': wh.name, 'code': wh.code or '',
             'quantity': round(by_wh.get(wh_id, 0.0), 4),
             'product_count': sum(1 for qty in products_by_wh[wh_id].values() if qty)}
            for wh_id, wh in snapshot['warehouses'].items()
        ]
