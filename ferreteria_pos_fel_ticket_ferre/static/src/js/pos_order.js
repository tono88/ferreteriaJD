/** @odoo-module **/

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    export_for_printing(baseUrl, headerData) {
        const receipt = super.export_for_printing(...arguments);
        receipt.fel_ticket = this.ferreteriaFelTicket || {
            enabled: false,
            status: "not_loaded",
        };

        // The standard POS QR invites the customer to request an invoice.
        // Once an actual invoice/FEL ticket is present, that invitation is no
        // longer applicable and would be confusing beside the FEL data.
        if (receipt.fel_ticket.enabled) {
            receipt.pos_qr_code = false;
        }
        return receipt;
    },
});
