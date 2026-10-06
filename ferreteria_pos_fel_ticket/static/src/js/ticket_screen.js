/** @odoo-module **/

import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";
import { loadFerreteriaTicketData } from "./ticket_loader";

patch(TicketScreen.prototype, {
    async print(order) {
        // Una reimpresión vuelve a consultar el estado vigente, pero no crea
        // secuencias ni documentos nuevos.
        await loadFerreteriaTicketData(this.pos, order);
        return await super.print(...arguments);
    },
});
