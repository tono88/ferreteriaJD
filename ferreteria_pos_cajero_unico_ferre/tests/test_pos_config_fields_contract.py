"""Regresión Odoo 18: [] significa TODOS los campos del modelo pos.config.

Prueba de contrato sin instalar Odoo. Ejecutar:
python ferreteria_pos_cajero_unico_ferre/tests/test_pos_config_fields_contract.py
"""
import ast
from pathlib import Path


class ApiStub:
    @staticmethod
    def model(func):
        return func


class Parent:
    fields_to_load = []

    def _load_pos_data_fields(self, config_id):
        return self.fields_to_load


path = Path(__file__).resolve().parents[1] / "models" / "pos_config.py"
tree = ast.parse(path.read_text(encoding="utf-8"))
pos_config = next(
    item for item in tree.body
    if isinstance(item, ast.ClassDef) and item.name == "PosConfig"
)
method = next(
    item for item in pos_config.body
    if isinstance(item, ast.FunctionDef) and item.name == "_load_pos_data_fields"
)
sample = ast.Module(
    body=[
        ast.ClassDef(
            name="TestModel", bases=[ast.Name(id="Parent", ctx=ast.Load())],
            keywords=[], body=[method], decorator_list=[]
        )
    ],
    type_ignores=[],
)
space = {"api": ApiStub, "Parent": Parent}
exec(compile(ast.fix_missing_locations(sample), str(path), "exec"), space)
model = space["TestModel"]()

# El retorno vacío implica que Odoo carga todos los campos, incluido
# use_pricelist. Convertirlo en una lista de uno rompe _load_pos_data().
model.fields_to_load = []
assert model._load_pos_data_fields(2) == [], "No se deben restringir todos los campos"

# Otro módulo sí puede indicar una lista explícita; añadir nuestro campo.
model.fields_to_load = ["id", "use_pricelist"]
assert model._load_pos_data_fields(2) == [
    "id", "use_pricelist", "ferreteria_cajero_unico"
]
assert model.fields_to_load == ["id", "use_pricelist"], "No mutar la lista de terceros"

# Evitar duplicar el campo si otro addon ya lo incluyó.
model.fields_to_load = ["id", "ferreteria_cajero_unico", "use_pricelist"]
assert model._load_pos_data_fields(2) == model.fields_to_load
print("OK: pos.config conserva todos los campos y use_pricelist.")
