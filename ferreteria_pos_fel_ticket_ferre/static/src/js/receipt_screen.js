/** @odoo-module **/

import { onWillStart } from "@odoo/owl";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";

const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup(...arguments);
        onWillStart(async () => {
            await this.loadFerreteriaFelTicketData();
        });
    },

    async loadFerreteriaFelTicketData() {
        const order = this.currentOrder;
        if (!order) {
            return;
        }

        let lastResult = {
            enabled: false,
            status: "not_loaded",
        };

        // The order/invoice is normally created in the same server transaction.
        // A short retry window covers FEL providers that finish assigning the
        // UUID a moment after the order reaches the receipt screen.
        for (let attempt = 0; attempt < 8; attempt++) {
            try {
                lastResult = await this.pos.data.call(
                    "pos.order",
                    "get_fel_ticket_data_for_pos",
                    [
                        typeof order.id === "number" ? order.id : false,
                        order.pos_reference || order.name || "",
                        order.uuid || "",
                    ]
                );
                order.ferreteriaFelTicket = lastResult || {
                    enabled: false,
                    status: "empty_response",
                };

                if (
                    lastResult?.certified ||
                    ["not_invoiced", "not_found", "access_denied"].includes(lastResult?.status)
                ) {
                    break;
                }
            } catch (error) {
                console.warn("No fue posible cargar los datos FEL del ticket POS.", error);
                order.ferreteriaFelTicket = {
                    enabled: false,
                    status: "rpc_error",
                };
                break;
            }
            await sleep(600);
        }
    },
});
