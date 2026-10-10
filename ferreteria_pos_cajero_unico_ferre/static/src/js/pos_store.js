/** Copyright 2026 Ferretería JD. LGPL-3.
 * Identidad fija: usuario autenticado en Odoo, sin PIN adicional.
 * Se aplica solo si el administrador activó cajero único en ese POS.
 */
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    set_cashier(cashier) {
        if (this.config?.ferreteria_cajero_unico && !this.config.module_pos_hr) {
            // No confiar en un cajero distinto guardado en sessionStorage ni
            // en selecciones antiguas. Odoo autentica a this.user.
            cashier = this.user || cashier;
        }
        return super.set_cashier(cashier);
    },

    get firstScreen() {
        if (this.config?.ferreteria_cajero_unico && !this.config.module_pos_hr) {
            if (this.user) {
                this.set_cashier(this.user);
                return "ProductScreen";
            }
            return "LoginScreen";
        }
        return super.firstScreen;
    },
});
