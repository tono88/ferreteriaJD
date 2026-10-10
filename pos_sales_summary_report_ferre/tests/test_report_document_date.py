"""Pruebas de selección de registros con facturas y fechas distintas.

Extraemos el método del AST para validar su lógica sin iniciar un Odoo real.
"""
import ast
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

start_code = Path(__file__).resolve().parents[1] / "report" / "report_pos_sales_summary.py"
tree = ast.parse(start_code.read_text(encoding="utf-8"))
klass = next(x for x in tree.body if isinstance(x, ast.ClassDef) and x.name == "ReportPosSalesSummary")
method = next(x for x in klass.body if isinstance(x, ast.FunctionDef) and x.name == "_search_orders")
test_ast = ast.Module(body=[
    ast.ClassDef(name="ReportProxy", bases=[], keywords=[], body=[method], decorator_list=[]),
], type_ignores=[])
namespace = {"datetime": datetime}
exec(compile(ast.fix_missing_locations(test_ast), str(start_code), "exec"), namespace)


class RecordSet(list):
    def filtered(self, fn):
        return RecordSet(filter(fn, self))

    def sorted(self, key):
        return RecordSet(sorted(self, key=key))

    def __or__(self, other):
        result = RecordSet(self)
        for value in other:
            if value not in result:
                result.append(value)
        return result


class OrderSearch:
    def __init__(self, rows):
        self.rows = RecordSet(rows)

    def search(self, domain):
        def matched(order, field, operator, rhs):
            val = order
            for name in field.split("."):
                val = getattr(val, name, None)
                if val is None:
                    break
            if val is None:
                return operator == "=" and rhs is False
            if isinstance(val, datetime):
                val = val.strftime("%Y-%m-%d %H:%M:%S")
            if hasattr(val, "isoformat") and not isinstance(val, (int, str)):
                val = val.isoformat()
            if operator == "in":
                return val in rhs
            if operator == ">=":
                return val >= rhs
            if operator == "<=":
                return val <= rhs
            if operator == "<":
                return val < rhs
            if operator == "=":
                return val == rhs
            raise AssertionError((field, operator))
        return RecordSet([
            order for order in self.rows
            if all(matched(order, *token) for token in domain if isinstance(token, tuple))
        ])


def sample(name, stamp, invoice_date=None, posted=True):
    invoice = SimpleNamespace(
        state="posted" if posted else "draft", invoice_date=invoice_date
    ) if invoice_date or not posted else None
    return SimpleNamespace(
        name=name,
        state="paid",
        amount_total=100.0,
        account_move=invoice,
        date_order=datetime.fromisoformat(stamp),
        partner_id=SimpleNamespace(id=1),
    )


orders = RecordSet([
    sample("A", "2026-10-08 05:50:00", "2026-10-07"),  # 7 local
    sample("B", "2026-10-08 06:20:00", "2026-10-08"),  # 8 local
    sample("C", "2026-10-08 13:00:00", "2026-10-07"),  # 8 POS, 7 factura
    sample("D", "2026-10-07 21:00:00", "2026-10-08"),  # 7 POS, 8 factura
    sample("E", "2026-10-09 05:50:00"),                # 8 local, sin factura
    sample("F", "2026-10-09 06:00:00"),                # 9 local
    sample("G", "2026-10-08 16:00:00", "2026-10-07", posted=False),
])

report = namespace["ReportProxy"]()
report._normalize_pos_config_id = lambda data: None
report._has_valid_invoice = lambda order: bool(order.account_move and order.account_move.state == "posted")
report.env = {"pos.order": OrderSearch(orders)}

params = {
    "date_from": "2026-10-08",
    "date_to": "2026-10-08",
    "start_utc": "2026-10-08 06:00:00",
    "end_utc": "2026-10-09 06:00:00",
    "invoice_filter": "all",
}

actual_doc = {o.name for o in report._search_orders({**params, "date_basis": "document"})}
assert actual_doc == {"B", "D", "E", "G"}, actual_doc
# En modo fecha POS se incluye C (operación el 8, factura con fecha 7),
# y no D (factura del 8, operación POS del 7).
actual_pos = {o.name for o in report._search_orders({**params, "date_basis": "order"})}
assert actual_pos == {"B", "C", "E", "G"}, actual_pos
print("OK: documento vs. operación POS y corte al día 8 GT.")
