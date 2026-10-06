/** @odoo-module **/

const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

export async function loadFerreteriaTicketData(pos, order, options = {}) {
    if (!order) {
        return { enabled: false, status: "not_loaded" };
    }
    const attempts = options.attempts || 8;
    const delay = options.delay || 600;
    let lastResult = { enabled: false, status: "not_loaded" };

    for (let attempt = 0; attempt < attempts; attempt++) {
        try {
            lastResult = await pos.data.call(
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
            console.warn("No fue posible cargar los datos del ticket térmico.", error);
            order.ferreteriaFelTicket = {
                enabled: false,
                status: "rpc_error",
            };
            break;
        }
        await sleep(delay);
    }
    return order.ferreteriaFelTicket;
}
