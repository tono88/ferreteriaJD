/** @odoo-module **/

import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { patch } from "@web/core/utils/patch";

patch(Orderline, {
    props: {
        ...Orderline.props,
        line: {
            ...Orderline.props.line,
            shape: {
                ...Orderline.props.line.shape,
                ferreQty: { type: String, optional: true },
                ferreUnit: { type: String, optional: true },
                ferreUnitPrice: { type: String, optional: true },
                ferreLineTotal: { type: String, optional: true },
            },
        },
    },
});
