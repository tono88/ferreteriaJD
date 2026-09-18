from odoo import api, fields, models
from odoo.tools.float_utils import float_round
from odoo.tools.misc import formatLang, get_lang


PURCHASE_PRICE_DIGITS = (16, 8)


def _format_purchase_price(env, value):
    """Format with 2..8 decimals without changing monetary rounding."""
    formatted = formatLang(env, value or 0.0, digits=8)
    decimal_point = get_lang(env).decimal_point
    if decimal_point not in formatted:
        return f"{formatted}{decimal_point}00"
    integer, decimal = formatted.rsplit(decimal_point, 1)
    decimal = decimal.rstrip("0")
    decimal = decimal.ljust(2, "0")
    return f"{integer}{decimal_point}{decimal}"


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    price_unit = fields.Float(digits=PURCHASE_PRICE_DIGITS)

    def ferreteria_format_purchase_price(self):
        self.ensure_one()
        return _format_purchase_price(self.env, self.price_unit)


class ProductSupplierInfo(models.Model):
    _inherit = "product.supplierinfo"

    price = fields.Float(digits=PURCHASE_PRICE_DIGITS)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    # Odoo uses one field for customer and vendor document lines. Eight-digit
    # storage is required here so a bill created from a PO does not lose the
    # PO unit price. Views/reports below apply the special presentation only to
    # vendor documents; monetary totals retain the currency precision.
    price_unit = fields.Float(digits=PURCHASE_PRICE_DIGITS)

    @api.model
    def _ferreteria_is_vendor_move_type(self, move_type):
        return move_type in ("in_invoice", "in_refund", "in_receipt")

    @api.model
    def _ferreteria_standard_product_price(self, value):
        precision = self.env["decimal.precision"].precision_get("Product Price")
        return float_round(value or 0.0, precision_digits=precision)

    @api.model_create_multi
    def create(self, vals_list):
        guarded_vals = []
        for vals in vals_list:
            vals = dict(vals)
            if "price_unit" in vals:
                move_type = self.env.context.get("default_move_type")
                if vals.get("move_id"):
                    move_type = self.env["account.move"].browse(vals["move_id"]).move_type
                if not self._ferreteria_is_vendor_move_type(move_type):
                    vals["price_unit"] = self._ferreteria_standard_product_price(
                        vals["price_unit"]
                    )
            guarded_vals.append(vals)
        return super().create(guarded_vals)

    def write(self, vals):
        if "price_unit" not in vals:
            return super().write(vals)
        vendor_lines = self.filtered(
            lambda line: self._ferreteria_is_vendor_move_type(line.move_type)
        )
        other_lines = self - vendor_lines
        result = True
        if vendor_lines:
            result = super(AccountMoveLine, vendor_lines).write(vals)
        if other_lines:
            standard_vals = dict(vals)
            standard_vals["price_unit"] = self._ferreteria_standard_product_price(
                vals["price_unit"]
            )
            result = super(AccountMoveLine, other_lines).write(standard_vals) and result
        return result

    def ferreteria_format_purchase_price(self):
        self.ensure_one()
        return _format_purchase_price(self.env, self.price_unit)
