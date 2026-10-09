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
                cart.pricelist_id?.id || false, cart.fiscal_position_id?.id || false,
            ]);
        } catch (error) {
            console.error("Error al guardar cotización POS", error);
            this.dialog.add(AlertDialog, {
                title: _t("No se pudo crear la cotización"),
                body: _t("Revise permisos, productos, almacén y conexión. La venta sigue intacta."),
            });
            return;
        }
        // La cotización NO factura ni descuenta existencias.
        // No debe quedar un carrito duplicado después de guardarla.
        for (const line of cartLines) {
            line.delete();
        }
        cart.set_partner(false);
        const confirm = await ask(this.dialog, {
            title: _t("Cotización creada: %s", quotation.name),
            body: _t(
                "Almacén: %s. ¿Desea cargarla en el POS para cobrar y generar UNA factura? " +
                "El pedido se confirma al finalizar el cobro, no antes.",
                quotation.warehouse
            ),
            confirmLabel: _t("Confirmar y cobrar"),
            cancelLabel: _t("Guardar cotización"),
        });
        if (confirm) {
            try {
                await this.pos.ferreteriaLoadQuotationToPayment(quotation.id);
            } catch (error) {
                console.error("Error cargando la cotización al POS", error);
                this.pos.notification.add(
                    _t("Cotización guardada, pero no se pudo cargar para el cobro. " +
                       "Abra la lista de cotizaciones y vuelva a intentarlo."),
                    { type: "danger" }
                );
            }
        } else {
            this.pos.notification.add(
                _t("Cotización %s guardada sin factura ni movimiento de inventario.", quotation.name),
                { type: "success" }
            );
        }
    },
});
