/** @odoo-module **/

import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { formatFloat } from "@web/core/utils/numbers";
import { patch } from "@web/core/utils/patch";

const DISPLAY_DECIMALS = 6;

function formatAmount(value, currency) {
    const amount = formatFloat(Number(value) || 0, {
        digits: [69, DISPLAY_DECIMALS],
        trailingZeros: false,
    });
    if (!currency?.symbol) {
        return amount;
    }
    return currency.position === "after"
        ? `${amount}\u00a0${currency.symbol}`
        : `${currency.symbol}\u00a0${amount}`;
}

patch(PosOrderline.prototype, {
    getDisplayData() {
        const data = super.getDisplayData(...arguments);
        return {
            ...data,
            ferreUnitPrice: formatAmount(this.get_unit_display_price(), this.currency),
            ferreLineTotal: formatAmount(this.get_display_price(), this.currency),
        };
    },
});

