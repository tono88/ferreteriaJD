/** Copyright 2026 Ferretería JD. LGPL-3. */
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { ask } from "@point_of_sale/app/store/make_awaitable_dialog";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(ControlButtons.prototype, {
    async clickCreateFerreteriaQuotation() {
        const cart = this.pos.get_order();
        const partner = cart.get_partner();
        if (!partner) {
            this.dialog.add(AlertDialog, {
                title: _t("Falta el cliente"),
                body: _t("Seleccione un cliente para crear la cotización."),
            });
            return;
        }
        const cartLines = [...cart.get_orderlines()];
        if (!cartLines.length) {
            this.dialog.add(AlertDialog, {
                title: _t("Cotización vacía"),
                body: _t("Agregue al menos un producto."),
            });
            return;
        }
        const items = cartLines.map((line) => ({
            product_id: line.get_product().id,
            quantity: line.qty,
            price_unit: line.price_unit,
            discount: line.discount,
        }));
        let quotation;
        try {
            quotation = await this.pos.data.call("sale.order", "create_quotation_from_pos", [
                partner.id, items, this.pos.config.id,
            ]);
        } catch (error) {
            this.dialog.add(AlertDialog, {
                title: _t("No se pudo crear la cotización"),
                body: _t("Revise los permisos, productos y la conexión. No se ha vaciado la venta."),
            });
            return;
        }
        // Borrar el carrito solo después de que el servidor confirme la creación.
        for (const line of cartLines) {
            line.delete();
        }
        cart.set_partner(false);
        const confirm = await ask(this.dialog, {
            title: _t("Cotización creada: %s", quotation.name),
            body: _t("¿Desea confirmarla como pedido de venta? Si no, permanecerá como cotización."),
            confirmLabel: _t("Confirmar pedido"),
            cancelLabel: _t("Dejar como cotización"),
        });
        if (confirm) {
            try {
                await this.pos.data.call("sale.order", "action_confirm", [[quotation.id]]);
                this.pos.notification.add(_t("Pedido confirmado."), { type: "success" });
            } catch (error) {
                this.pos.notification.add(_t("Cotización guardada, pero no se pudo confirmar."), {
                    type: "warning",
                });
            }
        }
    },
});
