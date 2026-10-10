"""Pruebas independientes de Odoo para fechas del reporte (python + pytz)."""
from datetime import date, datetime
from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path
from types import SimpleNamespace


p = Path(__file__).resolve().parents[1] / "models" / "report_timezone.py"
spec = spec_from_file_location("report_timezone", p)
mod = module_from_spec(spec)
spec.loader.exec_module(mod)

company = SimpleNamespace(partner_id=SimpleNamespace(tz=None))
assert mod.resolve_report_timezone(company) == "America/Guatemala"
company.partner_id.tz = "Invalid/Zone"
assert mod.resolve_report_timezone(company) == "America/Guatemala"
company.partner_id.tz = "America/Costa_Rica"
assert mod.resolve_report_timezone(company) == "America/Costa_Rica"

start, end = mod.local_report_utc_bounds(date(2026, 10, 8), date(2026, 10, 8), "America/Guatemala")
assert start == datetime(2026, 10, 8, 6, 0, 0), start
assert end == datetime(2026, 10, 9, 6, 0, 0), end

# La noche del 7 local, aunque el registro UTC tenga fecha del 8, se EXCLUYE.
assert datetime(2026, 10, 8, 5, 59, 59) < start
# La noche del 8 local, aunque el UTC sea día 9, se INCLUYE.
assert start <= datetime(2026, 10, 9, 5, 59, 59, 999999) < end
assert datetime(2026, 10, 9, 6, 0, 0) == end

# Países con horario de verano: día de 23 horas.
start, end = mod.local_report_utc_bounds(date(2026, 3, 8), date(2026, 3, 8), "America/New_York")
assert start == datetime(2026, 3, 8, 5, 0, 0)
assert end == datetime(2026, 3, 9, 4, 0, 0)
print("OK: cortes por empresa, límite exclusivo y cambio de horario.")
