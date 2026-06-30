/** @odoo-module **/

import { Component, onWillUnmount, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";

function errorMessage(error, fallback) {
    return (
        error?.data?.message ||
        error?.data?.arguments?.[0] ||
        error?.message ||
        fallback
    );
}

export class TransferRequestPopup extends Component {
    static template = "ferreteria_pos_transfer_request_ferre.TransferRequestPopup";
    static components = { Dialog };
    static props = {
        close: Function,
        posConfigId: Number,
        posConfigName: String,
        requestingWarehouseId: Number,
        requestingWarehouseName: String,
        supplyingWarehouses: Array,
        recentRequests: Array,
        currentPartner: { type: Object, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this._productSearchTimer = null;
        this._productBlurTimer = null;
        this._productSearchSequence = 0;
        const partnerResults = this.props.currentPartner ? [this.props.currentPartner] : [];
        this.state = useState({
            activeTab: "new",
            supplyingWarehouseId: "",
            requestNote: "",
            partnerSearch: "",
            selectedPartnerId: this.props.currentPartner?.id
                ? String(this.props.currentPartner.id)
                : "",
            partnerResults,
            searchingPartners: false,
            productSearch: "",
            productResults: [],
            productSearchOpen: false,
            highlightedProductIndex: -1,
            selectedProductId: "",
            requestedQty: 1,
            searchingProducts: false,
            lines: [],
            recentRequests: [...this.props.recentRequests],
            loadingRecent: false,
            submitting: false,
        });
        onWillUnmount(() => {
            if (this._productSearchTimer) {
                clearTimeout(this._productSearchTimer);
            }
            if (this._productBlurTimer) {
                clearTimeout(this._productBlurTimer);
            }
            this._productSearchSequence += 1;
        });
    }

    get selectedProduct() {
        const productId = Number(this.state.selectedProductId || 0);
        return this.state.productResults.find((product) => product.id === productId);
    }

    setTab(tab) {
        this.state.activeTab = tab;
    }

    _clearProductSearch({ keepText = false } = {}) {
        if (this._productSearchTimer) {
            clearTimeout(this._productSearchTimer);
            this._productSearchTimer = null;
        }
        if (this._productBlurTimer) {
            clearTimeout(this._productBlurTimer);
            this._productBlurTimer = null;
        }
        this._productSearchSequence += 1;
        if (!keepText) {
            this.state.productSearch = "";
        }
        this.state.productResults = [];
        this.state.productSearchOpen = false;
        this.state.highlightedProductIndex = -1;
        this.state.selectedProductId = "";
        this.state.searchingProducts = false;
    }

    async onSupplierChange() {
        if (this.state.lines.length) {
            this.state.lines.splice(0, this.state.lines.length);
            this.notification.add(
                _t("Se limpiaron las líneas porque cambió la sucursal suministradora."),
                { type: "warning" }
            );
        }
        this._clearProductSearch();
    }

    onProductSearchInput(event) {
        this.state.productSearch = event.target.value || "";
        this.state.selectedProductId = "";
        this._productSearchSequence += 1;
        this.state.highlightedProductIndex = -1;

        if (this._productSearchTimer) {
            clearTimeout(this._productSearchTimer);
        }

        const term = this.state.productSearch.trim();
        if (!this.state.supplyingWarehouseId || !term) {
            this.state.productResults = [];
            this.state.productSearchOpen = false;
            this.state.searchingProducts = false;
            return;
        }

        this._productSearchTimer = setTimeout(() => {
            this.searchProducts({ silentEmpty: true, openResults: true });
        }, 280);
    }

    onProductSearchFocus() {
        if (this.state.productResults.length && this.state.productSearch.trim()) {
            this.state.productSearchOpen = true;
        }
    }

    onProductSearchBlur() {
        // Delay closing so a pointer click on a suggestion can complete first.
        if (this._productBlurTimer) {
            clearTimeout(this._productBlurTimer);
        }
        this._productBlurTimer = setTimeout(() => {
            this.state.productSearchOpen = false;
            this._productBlurTimer = null;
        }, 180);
    }

    async onProductSearchKeydown(event) {
        const results = this.state.productResults;
        if (event.key === "ArrowDown") {
            event.preventDefault();
            if (!results.length) {
                await this.searchProducts({ silentEmpty: true, openResults: true });
                return;
            }
            this.state.productSearchOpen = true;
            this.state.highlightedProductIndex = Math.min(
                this.state.highlightedProductIndex + 1,
                results.length - 1
            );
            return;
        }
        if (event.key === "ArrowUp") {
            event.preventDefault();
            this.state.productSearchOpen = true;
            this.state.highlightedProductIndex = Math.max(
                this.state.highlightedProductIndex - 1,
                0
            );
            return;
        }
        if (event.key === "Escape") {
            event.preventDefault();
            this.state.productSearchOpen = false;
            return;
        }
        if (event.key !== "Enter") {
            return;
        }

        event.preventDefault();
        if (
            this.state.productSearchOpen &&
            this.state.highlightedProductIndex >= 0 &&
            results[this.state.highlightedProductIndex]
        ) {
            this.selectProduct(results[this.state.highlightedProductIndex]);
            return;
        }
        await this.searchProducts({
            silentEmpty: false,
            openResults: true,
            selectExact: true,
        });
    }

    onPartnerSearchKeydown(event) {
        if (event.key === "Enter") {
            event.preventDefault();
            this.searchPartners();
        }
    }

    async searchProducts({ silentEmpty = false, openResults = true, selectExact = false } = {}) {
        if (!this.state.supplyingWarehouseId) {
            this.notification.add(_t("Seleccione primero la sucursal suministradora."), {
                type: "warning",
            });
            return;
        }

        const sequence = ++this._productSearchSequence;
        this.state.searchingProducts = true;
        try {
            const result = await this.orm.call(
                "ferreteria.transfer.request",
                "pos_search_request_products",
                [
                    this.props.posConfigId,
                    Number(this.state.supplyingWarehouseId),
                    this.state.productSearch || "",
                    30,
                ]
            );
            if (sequence !== this._productSearchSequence) {
                return;
            }
            this.state.productResults = result.products || [];
            this.state.productSearchOpen = Boolean(openResults);
            this.state.highlightedProductIndex = this.state.productResults.length ? 0 : -1;

            if (selectExact && result.exact_match_id) {
                const exactProduct = this.state.productResults.find(
                    (product) => product.id === result.exact_match_id
                );
                if (exactProduct) {
                    this.selectProduct(exactProduct);
                    return;
                }
            }
            if (!this.state.productResults.length && !silentEmpty) {
                this.notification.add(_t("No se encontraron productos almacenables."), {
                    type: "warning",
                });
            }
        } catch (error) {
            if (sequence !== this._productSearchSequence) {
                return;
            }
            console.error("[Ferretería] Error buscando productos", error);
            this.notification.add(
                errorMessage(error, _t("No fue posible consultar los productos.")),
                { type: "danger" }
            );
        } finally {
            if (sequence === this._productSearchSequence) {
                this.state.searchingProducts = false;
            }
        }
    }

    selectProduct(product) {
        if (!product) {
            return;
        }
        this.state.selectedProductId = String(product.id);
        this.state.productSearch = product.name;
        this.state.productSearchOpen = false;
        this.state.highlightedProductIndex = -1;
    }

    clearSelectedProduct() {
        this._clearProductSearch();
    }

    setHighlightedProduct(index) {
        this.state.highlightedProductIndex = index;
    }

    async searchPartners() {
        this.state.searchingPartners = true;
        try {
            const result = await this.orm.call(
                "ferreteria.transfer.request",
                "pos_search_request_partners",
                [this.props.posConfigId, this.state.partnerSearch || "", 30]
            );
            const byId = new Map();
            if (this.props.currentPartner) {
                byId.set(this.props.currentPartner.id, this.props.currentPartner);
            }
            for (const partner of result || []) {
                byId.set(partner.id, partner);
            }
            this.state.partnerResults = [...byId.values()];
        } catch (error) {
            console.error("[Ferretería] Error buscando clientes", error);
            this.notification.add(
                errorMessage(error, _t("No fue posible consultar los clientes.")),
                { type: "danger" }
            );
        } finally {
            this.state.searchingPartners = false;
        }
    }

    addLine() {
        const product = this.selectedProduct;
        const qty = Number(this.state.requestedQty);
        if (!product) {
            this.notification.add(_t("Seleccione un producto de la lista de resultados."), {
                type: "warning",
            });
            return;
        }
        if (!Number.isFinite(qty) || qty <= 0) {
            this.notification.add(_t("Ingrese una cantidad mayor que cero."), {
                type: "warning",
            });
            return;
        }

        const existing = this.state.lines.find((line) => line.product_id === product.id);
        if (existing) {
            existing.qty += qty;
        } else {
            this.state.lines.push({
                product_id: product.id,
                product_name: product.name,
                default_code: product.default_code,
                barcode: product.barcode,
                uom_name: product.uom_name,
                tracking: product.tracking,
                available_qty: Number(product.available_qty || 0),
                qty,
                note: "",
            });
        }
        if (qty > Number(product.available_qty || 0)) {
            this.notification.add(
                _t(
                    "La cantidad supera la existencia libre mostrada. La disponibilidad se validará nuevamente al aprobar."
                ),
                { type: "warning" }
            );
        }
        this._clearProductSearch();
        this.state.requestedQty = 1;
    }

    removeLine(index) {
        this.state.lines.splice(index, 1);
    }

    resetForm() {
        this.state.supplyingWarehouseId = "";
        this.state.requestNote = "";
        this._clearProductSearch();
        this.state.requestedQty = 1;
        this.state.lines.splice(0, this.state.lines.length);
    }

    async submitRequest() {
        if (!this.state.supplyingWarehouseId) {
            this.notification.add(_t("Seleccione la sucursal suministradora."), {
                type: "warning",
            });
            return;
        }
        if (!this.state.lines.length) {
            this.notification.add(_t("Agregue al menos un producto."), {
                type: "warning",
            });
            return;
        }

        this.state.submitting = true;
        try {
            const result = await this.orm.call(
                "ferreteria.transfer.request",
                "pos_create_request_from_ui",
                [
                    this.props.posConfigId,
                    {
                        supplying_warehouse_id: Number(this.state.supplyingWarehouseId),
                        partner_id: Number(this.state.selectedPartnerId || 0) || false,
                        request_note: this.state.requestNote || "",
                        lines: this.state.lines.map((line) => ({
                            product_id: line.product_id,
                            qty: line.qty,
                            note: line.note || "",
                        })),
                    },
                ]
            );
            this.state.recentRequests = result.recent_requests || [];
            this.notification.add(
                _t("Solicitud %s enviada correctamente.", result.request_name),
                { type: "success" }
            );
            this.resetForm();
            this.state.activeTab = "status";
        } catch (error) {
            console.error("[Ferretería] Error creando solicitud POS", error);
            this.notification.add(
                errorMessage(error, _t("No fue posible enviar la solicitud.")),
                { type: "danger" }
            );
        } finally {
            this.state.submitting = false;
        }
    }

    async refreshRecentRequests() {
        this.state.loadingRecent = true;
        try {
            this.state.recentRequests = await this.orm.call(
                "ferreteria.transfer.request",
                "pos_get_recent_requests",
                [this.props.posConfigId, 20]
            );
        } catch (error) {
            console.error("[Ferretería] Error actualizando solicitudes", error);
            this.notification.add(
                errorMessage(error, _t("No fue posible actualizar los estados.")),
                { type: "danger" }
            );
        } finally {
            this.state.loadingRecent = false;
        }
    }

    formatQty(value) {
        const number = Number(value || 0);
        return Number.isFinite(number)
            ? number.toLocaleString(undefined, { maximumFractionDigits: 4 })
            : "0";
    }

    trackingLabel(tracking) {
        return {
            none: _t("Sin seguimiento"),
            lot: _t("Por lote"),
            serial: _t("Por número de serie"),
        }[tracking] || tracking || "";
    }

    stateClass(state) {
        return `o_ferreteria_request_state o_ferreteria_request_state_${state || "draft"}`;
    }
}
