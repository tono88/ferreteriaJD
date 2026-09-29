/** @odoo-module **/

import { ResPartner } from "@point_of_sale/app/models/res_partner";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { patch } from "@web/core/utils/patch";

export function normalizeNit(value) {
    return String(value || "")
        .replace(/[-\s]/g, "")
        .toLowerCase();
}

function isNitLike(value) {
    const normalized = normalizeNit(value);
    return Boolean(normalized) && /^(?:[0-9]+[0-9k]?|cf)$/i.test(normalized);
}

patch(ResPartner.prototype, {
    exactMatch(searchWord) {
        const normalizedSearch = normalizeNit(searchWord);
        const normalizedVat = normalizeNit(this.vat);
        return (
            super.exactMatch(searchWord) ||
            Boolean(normalizedSearch && normalizedVat && normalizedVat === normalizedSearch)
        );
    },
});

patch(PartnerList.prototype, {
    async getNewPartners() {
        if (isNitLike(this.state.query)) {
            const normalizedNit = normalizeNit(this.state.query);
            const exactNitMatches = await this.pos.data.searchRead(
                "res.partner",
                [["pos_nit_search_normalized", "=", normalizedNit]],
                [],
                { limit: 30, offset: this.state.currentOffset }
            );
            if (exactNitMatches.length) {
                return exactNitMatches;
            }
        }
        return super.getNewPartners(...arguments);
    },
});

