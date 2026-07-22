# -*- coding: utf-8 -*-
from odoo import _
from odoo.exceptions import ValidationError


def post_init_hook(env):
    """Register existing accounting bank references before enabling use."""
    registry = env["ferreteria.bank.slip.registry"]
    duplicates = []
    payments = env["account.payment"].with_context(active_test=False).search(
        [("bank_reference", "!=", False)], order="id"
    )
    for payment in payments:
        try:
            registry.claim(payment, payment.bank_reference)
        except ValidationError as error:
            duplicates.append(f"{payment.display_name}: {error}")
    if duplicates:
        raise ValidationError(
            _(
                "No se puede instalar la unicidad de boletas porque existen "
                "referencias duplicadas:\n%s"
            )
            % "\n".join(duplicates[:50])
        )
