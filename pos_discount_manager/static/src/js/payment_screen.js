/** Copyright 2025 Cybrosys Technologies Pvt. Ltd.
 * Adaptación Ferretería JD 2026. AGPL-3.
 * Códigos de un solo uso para descuentos por línea y descuentos globales.
 */
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { evaluatePosDiscounts } from "./discount_guard";

patch(PaymentScreen.prototype, {
    async _finalizeValidation() {
        // El cajero real proviene de pos_hr, no de this.pos.user (la cuenta que
        // abrió la sesión puede seguir siendo Administrator).
        const cashier = this.pos.get_cashier();
        const rawLimit = cashier?.limited_discount;
        const limit = Number(rawLimit);

        // Evitar que undefined se interprete como 0 ("sin límite") cuando
        // falta cargar hr.employee.limited_discount o no hay empleado conectado.
        if (
            !this.pos.config.module_pos_hr ||
            !cashier?.id ||
            rawLimit === undefined ||
            rawLimit === null ||
            rawLimit === "" ||
            !Number.isFinite(limit) ||
            limit < 0 ||
            limit > 100
        ) {
            this.notification.add(
                _t("No se pudo cargar el límite de descuento del cajero. " +
                   "Active el ingreso por empleados y vuelva a abrir la sesión del POS."),
                { type: "danger", title: _t("Configuración del cajero incompleta") }
            );
            return;
        }

        const product = this.pos.config.discount_product_id;
        const discountProductId = Number(
            product?.id || this.pos.config.raw?.discount_product_id || 0
        );
        const result = evaluatePosDiscounts(this.currentOrder, discountProductId, limit);
        if (!result.needsApproval) {
            return await super._finalizeValidation(...arguments);
        }

        const code = await makeAwaitable(this.dialog, NumberPopup, {
            title: _t("Autorización de descuento: %s", cashier.name),
            subtitle: _t(
                "Límite %s%%; aplicado %s%% (incluye descuentos globales). " +
                "Solicite al gerente un código de un solo uso.",
                limit.toFixed(2),
                result.effectivePercentage.toFixed(2)
            ),
            confirmButtonLabel: _t("Autorizar descuento"),
            formatDisplayedValue: (text) => String(text || "").replace(/./g, "•"),
            isValid: (value) => /^[0-9]{6}$/.test(String(value)),
        });
        if (!code) {
            return;
        }

        let response;
        try {
            response = await this.pos.data.call("pos.discount.otp", "consume_code", [
                String(code),
                cashier.id,
                this.pos.config.id,
                String(this.currentOrder.uuid || ""),
            ]);
        } catch (error) {
            console.error("Error validando código de descuento POS:", error);
            this.notification.add(
                _t("No se pudo verificar el código en el servidor. Revise la conexión."),
                { type: "danger" }
            );
            return;
        }
        if (!response?.approved) {
            this.notification.add(response?.message || _t("Código no autorizado."), {
                type: "danger",
                title: _t("Descuento rechazado"),
            });
            return;
        }
        this.notification.add(_t("Descuento aprobado para %s.", cashier.name), {
            type: "success",
        });
        return await super._finalizeValidation(...arguments);
    },
});
