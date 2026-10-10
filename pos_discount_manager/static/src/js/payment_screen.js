/** Copyright 2025 Cybrosys Technologies Pvt. Ltd.
 * Adaptación Ferretería JD 2026. AGPL-3.
 * Soporta selección de empleado POS y cajero único de cuenta Odoo.
 */
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { evaluatePosDiscounts } from "./discount_guard";

patch(PaymentScreen.prototype, {
    async _finalizeValidation() {
        const employeeMode = Boolean(this.pos.config.module_pos_hr);
        let cashierName;
        let cashierId;
        let rawLimit;
        if (employeeMode) {
            // Modalidad original pos_hr: cajero elegido por PIN/lector.
            const cashier = this.pos.get_cashier();
            cashierName = cashier?.name;
            cashierId = cashier?.id;
            rawLimit = cashier?.limited_discount;
        } else {
            // Cajero = cuenta Odoo. La asociación usuario->empleado se busca
            // exclusivamente en el servidor para impedir suplantar identidades.
            try {
                const policy = await this.pos.data.call(
                    "pos.discount.otp",
                    "get_logged_user_discount_policy",
                    [this.pos.config.id]
                );
                cashierName = policy.employee_name;
                cashierId = policy.employee_id;
                rawLimit = policy.limited_discount;
            } catch (error) {
                console.error("No se pudo resolver empleado de cuenta Odoo", error);
                this.notification.add(
                    _t("No se puede cobrar: compruebe que la cuenta de Odoo " +
                        "tenga un empleado activo asociado en esta empresa y " +
                        "que el POS esté en línea con una sesión abierta."),
                    { type: "danger", title: _t("Cajero sin empleado asignado") }
                );
                return;
            }
        }
        const limit = Number(rawLimit);
        if (
            !cashierId ||
            rawLimit === undefined ||
            rawLimit === null ||
            rawLimit === "" ||
            !Number.isFinite(limit) ||
            limit < 0 ||
            limit > 100
        ) {
            this.notification.add(
                _t("No se pudo cargar el límite del cajero. Revise el empleado " +
                   "asociado y vuelva a abrir el POS."),
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
            title: _t("Autorización de descuento: %s", cashierName),
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
            if (employeeMode) {
                response = await this.pos.data.call(
                    "pos.discount.otp", "consume_code",
                    [String(code), cashierId, this.pos.config.id,
                        String(this.currentOrder.uuid || "")]
                );
            } else {
                response = await this.pos.data.call(
                    "pos.discount.otp", "consume_code_for_logged_user",
                    [String(code), this.pos.config.id,
                        String(this.currentOrder.uuid || "")]
                );
            }
        } catch (error) {
            console.error("Error validando código de descuento POS:", error);
            this.notification.add(
                _t("No se pudo verificar el código en el servidor. Revise la conexión " +
                   "y que la sesión POS corresponda a su cuenta de Odoo."),
                { type: "danger" }
            );
            return;
        }
        if (!response?.approved) {
            this.notification.add(response?.message || _t("Código no autorizado."), {
                type: "danger", title: _t("Descuento rechazado"),
            });
            return;
        }
        this.notification.add(_t("Descuento aprobado para %s.", cashierName), {
            type: "success",
        });
        return await super._finalizeValidation(...arguments);
    },
});
