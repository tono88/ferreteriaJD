/** @odoo-module **/

import { onWillStart } from "@odoo/owl";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";
import { loadFerreteriaTicketData } from "./ticket_loader";

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup(...arguments);
        onWillStart(async () => {
            await this.loadFerreteriaFelTicketData();
        });
    },

    async loadFerreteriaFelTicketData() {
        await loadFerreteriaTicketData(this.pos, this.currentOrder);
    },
});
