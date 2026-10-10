/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ListController } from "@web/views/list/list_controller";
import { InventoryReportListView } from "@stock/views/list/inventory_report_list_view";

export class InventoryLocationReportListController extends ListController {
    setup() {
        super.setup();
        this.orm = useService("orm");
    }

    getReportPayload() {
        const searchModel = this.env.searchModel;
        const filterSummary = searchModel.facets
            .filter((facet) => facet.type !== "groupBy")
            .map((facet) => {
                const values = facet.values.join(` ${facet.separator || "o"} `);
                return facet.title ? `${facet.title}: ${values}` : values;
            })
            .filter(Boolean)
            .join("; ");
        return {
            domain: this.model.root.domain,
            filter_summary: filterSummary || "Sin filtros adicionales",
            domain_display: searchModel.domainString,
        };
    }

    async onPrintLocationPdf() {
        const payload = this.getReportPayload();
        const action = await this.orm.call(
            "stock.quant",
            "action_print_location_report",
            [payload.domain, payload.filter_summary, payload.domain_display],
            { context: this.props.context }
        );
        await this.actionService.doAction(action);
    }

    async onExportLocationXlsx() {
        const payload = this.getReportPayload();
        const action = await this.orm.call(
            "stock.quant",
            "action_export_location_report_xlsx",
            [payload.domain, payload.filter_summary, payload.domain_display],
            { context: this.props.context }
        );
        await this.actionService.doAction(action);
    }
}

export const InventoryLocationReportListView = {
    ...InventoryReportListView,
    Controller: InventoryLocationReportListController,
    buttonTemplate: "ferreteria_inventory_location_report_ferre.ListView.Buttons",
};

registry
    .category("views")
    .add("ferreteria_inventory_location_report_list", InventoryLocationReportListView);

