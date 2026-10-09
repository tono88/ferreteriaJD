// Pruebas del cálculo de límites sin necesitar una instancia Odoo.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
(async () => {
    const modulePath = path.join(__dirname, "../static/src/js/discount_guard.js");
    const source = fs.readFileSync(modulePath, "utf8");
    const { evaluatePosDiscounts } = await import(
        "data:text/javascript;base64," + Buffer.from(source).toString("base64")
    );
    const saleLine = (discount = 0) => ({
        get_product: () => ({ id: 101 }),
        get_discount: () => discount,
        get_quantity: () => 1,
        get_unit_price: () => 100,
        isGlobalDiscountApplicable: () => true,
    });
    const globalLine = (price) => ({
        get_product: () => ({ id: 999 }),
        get_discount: () => 0,
        get_quantity: () => 1,
        get_unit_price: () => price,
    });
    const order = (lines, base = 100) => ({
        get_orderlines: () => lines,
        calculate_base_amount: () => base,
    });
    assert.equal(evaluatePosDiscounts(order([saleLine(2)]), 999, 1).needsApproval, true);
    assert.equal(evaluatePosDiscounts(order([saleLine(0.5)]), 999, 1).needsApproval, false);
    assert.equal(evaluatePosDiscounts(order([saleLine(), globalLine(-2)]), 999, 1).needsApproval, true);
    assert.equal(evaluatePosDiscounts(order([saleLine(), globalLine(-0.5)]), 999, 1).needsApproval, false);
    assert.equal(evaluatePosDiscounts(order([saleLine(0.7), globalLine(-0.7)]), 999, 1).needsApproval, true);
    assert.equal(evaluatePosDiscounts(order([saleLine(10)]), 999, 0).needsApproval, false);
    assert.equal(evaluatePosDiscounts(order([saleLine(), globalLine(-2)], 0), 999, 1).needsApproval, true);
    console.log("OK: descuentos de línea, globales y acumulados.");
})().catch((error) => { console.error(error); process.exitCode = 1; });
