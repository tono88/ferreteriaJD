/** Copyright 2025 Cybrosys Technologies Pvt. Ltd.
 * Adaptación Ferretería JD 2026. AGPL-3.
 * El código se valida en el servidor y se consume una sola vez.
 */
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";

patch(PaymentScreen.prototype, {
    async _finalizeValidation() {
        const cashier = this.pos.get_cashier();
        const limit = Number(cashier?.limited_discount ?? 0);
        const lines = this.currentOrder.get_orderlines();
        // Se conserva la convención del módulo original: 0 equivale a sin límite.
        const needsApproval = limit !== 0 && lines.some(
            (line) => Number(line.discount) > limit
        );
        if (!needsApproval) {
            return await super._finalizeValidation(...arguments);
        }
        if (!cashier?.id || !this.pos.config?.id) {
            this.notification.add(_t("No se identificó al cajero o punto de venta."), {
                type: "danger",
            });
            return;
        }
        const code = await makeAwaitable(this.dialog, NumberPopup, {
            title: _t("Descuento fuera del límite de %s. Ingrese el código temporal del gerente.", cashier.name),
            confirmButtonLabel: _t("Autorizar"),
            isValid: (value) => /^\\d{6}$/.test(String(value)),
        });
        if (!code) {
            return; // Cancelación de diálogo: no se cobra ni se consume código.
        }
        let result;
        try {
            result = await this.pos.data.call("pos.discount.otp", "consume_code", [
                String(code),
                cashier.id,
                this.pos.config.id,
                String(this.currentOrder.uuid || ""),
            ]);
        } catch (error) {
            this.notification.add(_t("No se pudo comprobar el código. Revise su conexión."), {
                type: "danger",
            });
            return;
        }
        if (!result?.approved) {
            this.notification.add(result?.message || _t("No autorizado."), {
                type: "danger",
                title: _t("Descuento rechazado"),
            });
            return;
        }
        this.notification.add(_t("Descuento autorizado con código de un solo uso."), {
            type: "success",
        });
        return await super._finalizeValidation(...arguments);
    },
});
