/** @odoo-module **/

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { loadFerreteriaTicketData } from "./ticket_loader";

patch(PaymentScreen.prototype, {
    async afterOrderValidation() {
        // Odoo puede imprimir automáticamente dentro de super(). Cargamos los
        // datos del servidor antes para que una venta FEL nunca se imprima con
        // UUID/serie/número todavía ausentes.
        await loadFerreteriaTicketData(this.pos, this.currentOrder);
        return await super.afterOrderValidation(...arguments);
    },
});
