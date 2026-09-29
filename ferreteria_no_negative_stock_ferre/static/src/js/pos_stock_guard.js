/** @odoo-module **/

import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { roundPrecision } from "@web/core/utils/numbers";


function isStorable(product) {
    return Boolean(product?.is_storable || product?.type === "product");
}


function positiveQuantityForProduct(order, product, currentLine, candidateQuantity) {
    return order.lines.reduce((total, line) => {
        if (line.product_id?.id !== product.id) {
            return total;
        }
        const quantity = line === currentLine ? candidateQuantity : line.get_quantity();
        return total + quantity;
    }, 0);
}


function consumeLocalSnapshot(order) {
    const totals = new Map();
    for (const line of order.lines) {
        const product = line.product_id;
        if (!isStorable(product)) {
            continue;
        }
        totals.set(product, (totals.get(product) || 0) + line.get_quantity());
    }
    for (const [product, quantity] of totals) {
        if (quantity > 0 && Number.isFinite(product.ferreteria_pos_available_qty)) {
            product.ferreteria_pos_available_qty -= quantity;
        }
    }
}


patch(PosOrderline.prototype, {
    set_quantity(quantity, keepPrice) {
        const candidate =
            typeof quantity === "number" ? quantity : parseFloat(String(quantity || 0));
        const product = this.product_id;
        const available = product?.ferreteria_pos_available_qty;

        if (
            isStorable(product) &&
            Number.isFinite(candidate) &&
            Number.isFinite(available)
        ) {
            const requested = positiveQuantityForProduct(
                this.order_id,
                product,
                this,
                candidate
            );
            const rounding = product.uom_id?.rounding || 0.01;
            if (roundPrecision(requested - available, rounding) > 0) {
                return {
                    title: _t("Stock insuficiente"),
                    body: _t(
                        "Disponible en esta sucursal: %(available)s %(uom)s. " +
                            "Total solicitado en la orden: %(requested)s %(uom)s.",
                        {
                            available: roundPrecision(available, rounding),
                            requested: roundPrecision(requested, rounding),
                            uom: product.uom_id?.name || "",
                        }
                    ),
                };
            }
        }

        return super.set_quantity(quantity, keepPrice);
    },
});


patch(PaymentScreen.prototype, {
    async _finalizeValidation() {
        const order = this.currentOrder;
        const result = await super._finalizeValidation(...arguments);
        if (order.state !== "draft" && !order._ferreteriaStockSnapshotConsumed) {
            consumeLocalSnapshot(order);
            order._ferreteriaStockSnapshotConsumed = true;
        }
        return result;
    },
});

export { consumeLocalSnapshot, isStorable, positiveQuantityForProduct };
