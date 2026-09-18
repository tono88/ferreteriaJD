/** @odoo-module **/

import { localization } from "@web/core/l10n/localization";
import { registry } from "@web/core/registry";
import { FloatField, floatField } from "@web/views/fields/float/float_field";
import { formatFloat } from "@web/views/fields/formatters";


export function formatPurchasePrice(value) {
    const formatted = formatFloat(value, {
        digits: [16, 8],
        humanReadable: false,
        trailingZeros: false,
    });
    const decimalPoint = localization.decimalPoint;
    if (!formatted.includes(decimalPoint)) {
        return `${formatted}${decimalPoint}00`;
    }
    const parts = formatted.split(decimalPoint);
    const decimals = (parts.pop() || "").padEnd(2, "0");
    return `${parts.join(decimalPoint)}${decimalPoint}${decimals}`;
}


export class PurchasePriceField extends FloatField {
    get formattedValue() {
        const fields = this.props.record.fields;
        const moveType = this.props.record.data.move_type;
        if (
            "move_type" in fields &&
            !["in_invoice", "in_refund", "in_receipt"].includes(moveType)
        ) {
            return super.formattedValue;
        }
        return formatPurchasePrice(this.value);
    }
}


export const purchasePriceField = {
    ...floatField,
    component: PurchasePriceField,
};

registry.category("fields").add("ferreteria_purchase_price_8", purchasePriceField);
