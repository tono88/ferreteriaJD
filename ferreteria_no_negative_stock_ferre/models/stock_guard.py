# -*- coding: utf-8 -*-
"""Shared stock validation helpers.

This module intentionally contains plain Python helpers instead of an Odoo
``AbstractModel``.  The validator is reused by ``pos.order`` and ``sale.order``
without introducing a second ORM inheritance parent, which avoids copying the
standard models' relational fields during registry setup.
"""
from collections import defaultdict

from odoo import _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare


def _is_stock_tracked_product(product):
    """Return whether the product must be checked against warehouse stock."""
    return bool(
        product
        and (
            getattr(product, "is_storable", False)
            or getattr(product, "type", False) == "product"
        )
    )


def _lock_stock_keys(env, location, products):
    """Serialize checks for the same location/product combinations.

    PostgreSQL transaction-scoped advisory locks protect the stock read and
    reservation sequence from concurrent POS terminals.  They do not modify
    stock and are automatically released when the transaction finishes.
    """
    for product in products.sorted(key=lambda item: item.id):
        env.cr.execute(
            "SELECT pg_advisory_xact_lock(%s, %s)",
            (location.id, product.id),
        )


def validate_stock_requirements(
    env,
    *,
    location,
    requirements,
    warehouse_name,
):
    """Validate requested product quantities at one warehouse location.

    ``requirements`` is an iterable of ``(product, quantity_in_product_uom)``.
    Signed quantities may be supplied; only the positive net requirement is
    checked, so pure refunds never block.
    """
    totals = defaultdict(float)
    products_by_id = {}
    for product, quantity in requirements:
        if not _is_stock_tracked_product(product):
            continue
        totals[product.id] += quantity
        products_by_id[product.id] = product

    positive_products = env["product.product"]
    for product_id, quantity in totals.items():
        product = products_by_id[product_id]
        if float_compare(
            quantity,
            0.0,
            precision_rounding=product.uom_id.rounding,
        ) > 0:
            positive_products |= product

    if not positive_products:
        return True

    _lock_stock_keys(env, location, positive_products)

    shortages = []
    quant_model = env["stock.quant"].sudo()
    for product in positive_products.sorted(key=lambda item: item.display_name):
        requested = totals[product.id]
        available = quant_model._get_available_quantity(
            product,
            location,
            strict=False,
        )
        if float_compare(
            available,
            requested,
            precision_rounding=product.uom_id.rounding,
        ) < 0:
            shortages.append(
                _(
                    "%(product)s — disponible: %(available)s %(uom)s; "
                    "solicitado: %(requested)s %(uom)s"
                )
                % {
                    "product": product.display_name,
                    "available": available,
                    "requested": requested,
                    "uom": product.uom_id.display_name,
                }
            )

    if shortages:
        raise UserError(
            _(
                "No hay inventario suficiente en %(warehouse)s para completar "
                "la venta:\n\n%(lines)s"
            )
            % {
                "warehouse": warehouse_name,
                "lines": "\n".join(shortages),
            }
        )
    return True
