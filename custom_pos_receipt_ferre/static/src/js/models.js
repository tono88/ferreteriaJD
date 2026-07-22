/** @odoo-module **/

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    getReceiptHeaderData(order) {
        const data = super.getReceiptHeaderData(...arguments);
        return {
            ...data,
            partner: order?.partner_id || data.partner,
        };
    },
});
