/** Copyright 2026 Ferretería JD. LGPL-3.
 * Utiliza pos_sale.settleSO para ligar cada línea POS a su sale.order.line.
 */
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { ask, makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";

patch(PosStore.prototype, {
    async ferreteriaLoadQuotationToPayment(saleOrderId) {
        // Servidor: verificar POS/almacén, estados y si ya existe una factura.
        await this.data.call("sale.order", "ferreteria_validate_pos_checkout", [
            [saleOrderId], this.config.id,
        ]);
        const saleOrder = await this._getSaleOrder(saleOrderId);
        const currentOrder = this.get_order();
        const linked = currentOrder?.get_orderlines().some(
            (line) => line.sale_order_origin_id?.id === saleOrderId
        );
        if (linked) {
            // Evita agregar dos veces los artículos si el operador repite el botón.
            currentOrder.set_to_invoice(true);
            await this.pay();
            return;
        }
        if (currentOrder?.get_orderlines().length) {
            const startNew = await ask(this.dialog, {
                title: _t("Hay una venta en curso"),
                body: _t(
                    "Se abrirá otra orden POS para cobrar la cotización %s " +
                    "sin mezclar productos ni afectar la venta actual.",
                    saleOrder.name
                ),
                confirmLabel: _t("Abrir otra orden"),
                cancelLabel: _t("Volver"),
            });
            if (!startNew) {
                return;
            }
            this.add_new_order({});
        }
        const order = this.get_order();
        if (saleOrder.partner_id) {
            order.set_partner(saleOrder.partner_id);
        }
        order.update({ fiscal_position_id: saleOrder.fiscal_position_id });
        await this.settleSO(saleOrder, saleOrder.fiscal_position_id);
        // Factura FEL desde el POS. No se usa el asistente de factura de Ventas.
        order.set_to_invoice(true);
        await this.pay();
    },

    async onClickSaleOrder(saleOrderId) {
        const order = await this._getSaleOrder(saleOrderId);
        const isQuotation = ["draft", "sent"].includes(order.state);
        const choices = [];
        if (isQuotation) {
            choices.push(
                { id: "preview", item: "preview", label: _t("Visualizar cotización (PDF)") },
                { id: "email", item: "email", label: _t("Enviar cotización por correo") },
                { id: "print", item: "print", label: _t("Imprimir cotización (PDF)") },
                {
                    id: "confirm",
                    item: "confirm",
                    label: order.is_pos_created
                        ? _t("Confirmar y cobrar en POS (factura única)")
                        : _t("Confirmar pedido de venta"),
                }
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
                    console.error("Error al enviar cotización", error);
                    this.notification.add(_t("Verifique el correo del cliente y SMTP."), {
                        type: "danger",
                    });
                }
            }
            return;
        }
        if (choice === "confirm") {
            if (order.is_pos_created) {
                try {
                    await this.ferreteriaLoadQuotationToPayment(saleOrderId);
                } catch (error) {
                    console.error("Error en confirmar y cobrar cotización", error);
                    this.notification.add(_t(
                        "No se puede cargar la cotización. Revise que pertenezca a este POS, " +
                        "no esté facturada y tenga el almacén correcto."
                    ), { type: "danger" });
                }
            } else {
                await this.data.call("sale.order", "action_confirm", [[saleOrderId]]);
                this.notification.add(_t("Pedido confirmado."), { type: "success" });
            }
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
