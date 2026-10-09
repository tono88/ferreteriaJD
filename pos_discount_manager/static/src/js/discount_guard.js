/** Copyright 2026 Ferretería JD. AGPL-3.
 * Cálculo puro y verificable de descuentos efectivos de Odoo 18 POS.
 *
 * Odoo pos_discount NO usa line.discount para descuentos globales:
 * inserta líneas con discount_product_id y precio negativo.
 */

/**
 * @returns {{linePercentage:number,globalPercentage:number,effectivePercentage:number,needsApproval:boolean}}
 */
export function evaluatePosDiscounts(order, discountProductId, cashierLimit) {
    const lines = order.get_orderlines();
    const isGlobalLine = (line) =>
        Boolean(discountProductId) && line.get_product()?.id === discountProductId;
    const salesLines = lines.filter((line) => !isGlobalLine(line));
    const linePercentage = salesLines.reduce((max, line) => {
        const value = Number(line.get_discount?.() ?? line.discount ?? 0);
        return Math.max(max, Number.isFinite(value) ? value : 0);
    }, 0);

    const globalDiscountTotal = lines.filter(isGlobalLine).reduce((sum, line) => {
        const price = Number(line.get_unit_price?.() ?? line.price_unit ?? 0);
        const qty = Number(line.get_quantity?.() ?? line.qty ?? 0);
        return sum + Math.max(0, -(price * qty));
    }, 0);
    // Igualar la base de cálculo nativa de pos_discount (respeta impuestos
    // incluidos en precio y omite artículos no sujetos a descuento global).
    const applicableLines = salesLines.filter(
        (line) => line.isGlobalDiscountApplicable?.() ?? line.isDiscountable?.() ?? true
    );
    const base = globalDiscountTotal
        ? order.calculate_base_amount(applicableLines)
        : 0;
    const globalPercentage = globalDiscountTotal
        ? base > 0 ? Math.min(100, (globalDiscountTotal / base) * 100) : 100
        : 0;

    // Dos descuentos del 0.7 % no equivalen a uno del 0.7 %.
    // Se aplica un porcentaje después del otro.
    const effectivePercentage =
        100 * (1 - (1 - linePercentage / 100) * (1 - globalPercentage / 100));
    return {
        linePercentage,
        globalPercentage,
        effectivePercentage,
        needsApproval: cashierLimit > 0 && effectivePercentage > cashierLimit + 0.0001,
    };
}
