/** Copyright 2026 Ferretería JD. LGPL-3. */
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { ask, makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";

patch(PosStore.prototype, {
    async onClickSaleOrder(saleOrderId) {
        const order = await this._getSaleOrder(saleOrderId);
        const isQuotation = ["draft", "sent"].includes(order.state);
        const choices = [];
        if (isQuotation) {
            choices.push(
                { id: "preview", item: "preview", label: _t("Visualizar cotización (PDF)") },
                { id: "email", item: "email", label: _t("Enviar cotización por correo") },
                { id: "print", item: "print", label: _t("Imprimir cotización (PDF)") },
                { id: "confirm", item: "confirm", label: _t("Confirmar pedido") }
            );
        }
        if (order.state !== "cancel") {
            choices.push({ id: "cancel", item: "cancel", label: _t("Cancelar pedido") });
        }
        choices.push({ id: "standard", item: "standard", label: _t("Cobrar / anticipo (opciones originales)") });
        const choice = await makeAwaitable(this.dialog, SelectionPopup, {
            title: _t("Seleccione una acción para %s", order.name),
            list: choices,
        });
        if (!choice) {
            return;
        }
        if (choice === "standard") {
            return await super.onClickSaleOrder(saleOrderId);
        }
        if (choice === "preview") {
            return await this.action.doAction({
                type: "ir.actions.act_url",
                url: `/report/pdf/sale.report_saleorder/${saleOrderId}`,
                target: "new",
            });
        }
        if (choice === "print") {
            return await this.action.doAction({
                type: "ir.actions.report",
                report_type: "qweb-pdf",
                report_name: "sale.report_saleorder",
                report_file: "sale.report_saleorder",
                name: _t("Cotización"),
                context: { active_model: "sale.order", active_id: saleOrderId, active_ids: [saleOrderId] },
            });
        }
        if (choice === "email") {
            const email = order.partner_id?.email || _t("el correo del cliente");
            const approved = await ask(this.dialog, {
                title: _t("Enviar cotización"),
                body: _t("¿Enviar la cotización %s a %s?", order.name, email),
                confirmLabel: _t("Enviar correo"),
                cancelLabel: _t("Volver"),
            });
            if (approved) {
                try {
                    await this.data.call("sale.order", "pos_send_quotation_email", [[saleOrderId]]);
                    this.notification.add(_t("Cotización enviada por correo."), { type: "success" });
                } catch (error) {
                    this.notification.add(_t("No se pudo enviar. Verifique el correo del cliente y la configuración SMTP."), {
                        type: "danger",
                    });
                }
            }
            return;
        }
        if (choice === "confirm") {
            await this.data.call("sale.order", "action_confirm", [[saleOrderId]]);
            this.notification.add(_t("Pedido confirmado."), { type: "success" });
            return;
        }
        if (choice === "cancel") {
            const approved = await ask(this.dialog, {
                title: _t("Cancelar pedido"),
                body: _t("¿Seguro que desea cancelar %s?", order.name),
                confirmLabel: _t("Sí, cancelar"),
                cancelLabel: _t("No"),
            });
            if (approved) {
                await this.data.call("sale.order", "action_cancel", [[saleOrderId]], {
                    context: { disable_cancel_warning: true },
                });
                this.notification.add(_t("Pedido cancelado."), { type: "success" });
            }
        }
    },
});
