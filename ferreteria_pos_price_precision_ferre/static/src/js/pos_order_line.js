/** @odoo-module **/

import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { accountTaxHelpers } from "@account/helpers/account_tax";
import { formatFloat } from "@web/core/utils/numbers";
import { patch } from "@web/core/utils/patch";

const FALLBACK_PRICE_DECIMALS = 6;
const FALLBACK_QUANTITY_DECIMALS = 6;

function getDecimalPrecision(line, name, fallback) {
    return (
        line.models["decimal.precision"].find((precision) => precision.name === name)?.digits ??
        fallback
    );
}

function formatAmount(value, currency, decimals) {
    const amount = formatFloat(Number(value) || 0, {
        digits: [69, decimals],
        trailingZeros: false,
    });
    if (!currency?.symbol) {
        return amount;
    }
    return currency.position === "after"
        ? `${amount}\u00a0${currency.symbol}`
        : `${currency.symbol}\u00a0${amount}`;
}

function getPreciseUnitDisplayPrice(line, priceDecimals) {
    const product = line.get_product();
    const taxes = line.tax_ids || product.taxes_id;
    // The standard tax helper uses currency.rounding (Q0.01) while computing
    // its so-called raw base.  For this visual unit price only, use the Product
    // Price precision so 50.555555 is not irreversibly reduced to 50.56.
    // Totals and taxes still come from Odoo's untouched standard display data.
    const displayCurrency = {
        ...line.currency,
        rounding: 10 ** -priceDecimals,
    };
    const baseLine = accountTaxHelpers.prepare_base_line_for_taxes_computation(
        line,
        line.prepareBaseLineForTaxesComputationExtraValues({
            quantity: 1,
            tax_ids: taxes,
            currency_id: displayCurrency,
        })
    );

    // Keep Odoo's tax-included/tax-excluded semantics, without applying the
    // monetary rounding that belongs to totals rather than unit-price display.
    accountTaxHelpers.add_tax_details_in_base_line(baseLine, line.company);
    const taxDetails = baseLine.tax_details;
    return line.config.iface_tax_included === "total"
        ? taxDetails.raw_total_included_currency
        : taxDetails.raw_total_excluded_currency;
}

function formatQuantity(line) {
    return formatFloat(line.get_quantity(), {
        digits: [
            69,
            getDecimalPrecision(
                line,
                "Product Unit of Measure",
                FALLBACK_QUANTITY_DECIMALS
            ),
        ],
        trailingZeros: false,
    });
}

function formatUnitName(unitName, quantity) {
    if (Math.abs(quantity) === 1 && unitName === "Unidades") {
        return "Unidad";
    }
    return unitName;
}

patch(PosOrderline.prototype, {
    getDisplayData() {
        const data = super.getDisplayData(...arguments);
        const quantity = this.get_quantity();
        const priceDecimals = getDecimalPrecision(
            this,
            "Product Price",
            FALLBACK_PRICE_DECIMALS
        );
        return {
            ...data,
            ferreQty: formatQuantity(this),
            ferreUnit: formatUnitName(data.unit, quantity),
            ferreUnitPrice: formatAmount(
                getPreciseUnitDisplayPrice(this, priceDecimals),
                this.currency,
                priceDecimals
            ),
            // Preserve Odoo's standard monetary total and currency rounding.
            ferreLineTotal: data.price,
        };
    },
});
