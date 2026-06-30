/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { TransferRequestPopup } from "./transfer_request_popup";

function getErrorMessage(error) {
    return (
        error?.data?.message ||
        error?.data?.arguments?.[0] ||
        error?.message ||
        _t("No fue posible abrir las solicitudes entre sucursales.")
    );
}

patch(ControlButtons.prototype, {
    async openInterbranchRequests(event) {
        event?.stopPropagation();
        const orm = this.env.services.orm;
        const dialog = this.dialog;
        try {
            const data = await orm.call(
                "ferreteria.transfer.request",
                "pos_get_request_ui_data",
                [this.pos.config.id]
            );
            const partner = this.currentOrder?.get_partner();
            const popupProps = {
                posConfigId: data.pos_config_id,
                posConfigName: data.pos_config_name,
                requestingWarehouseId: data.requesting_warehouse_id,
                requestingWarehouseName: data.requesting_warehouse_name,
                supplyingWarehouses: data.supplying_warehouses || [],
                recentRequests: data.recent_requests || [],
            };
            if (partner) {
                popupProps.currentPartner = {
                    id: partner.id,
                    name: partner.display_name || partner.name,
                };
            }

            // Close only the standard Actions dialog before opening ours.
            if (this.props.close) {
                this.props.close();
            }
            dialog.add(TransferRequestPopup, popupProps);
        } catch (error) {
            console.error("[Ferretería] Error al abrir solicitudes POS", error);
            this.notification.add(getErrorMessage(error), { type: "danger" });
        }
    },
});
