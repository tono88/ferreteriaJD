# -*- coding: utf-8 -*-
import base64
import csv
import io
import json
import zipfile
import xml.etree.ElementTree as ET
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class VlfDashboardDataset(models.Model):
    _name = 'vlf.dashboard.dataset'
    _description = 'Dataset externo para dashboard'
    _order = 'write_date desc, name'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    source_type = fields.Selection([
        ('csv', 'CSV'),
        ('xlsx', 'Excel XLSX'),
    ], default='csv', required=True)
    filename = fields.Char()
    file_data = fields.Binary(string='Archivo CSV/XLSX')
    headers_json = fields.Text(default='[]')
    line_ids = fields.One2many('vlf.dashboard.dataset.line', 'dataset_id', string='Filas')
    row_count = fields.Integer(compute='_compute_row_count')
    parsed_at = fields.Datetime(readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.depends('line_ids')
    def _compute_row_count(self):
        for dataset in self:
            dataset.row_count = len(dataset.line_ids)

    def action_parse_file(self):
        for dataset in self:
            if not dataset.file_data:
                raise UserError(_('Sube un archivo primero.'))
            raw = base64.b64decode(dataset.file_data)
            if dataset.source_type == 'csv':
                rows = dataset._parse_csv(raw)
            elif dataset.source_type == 'xlsx':
                rows = dataset._parse_xlsx(raw)
            else:
                raise UserError(_('Tipo de archivo no soportado.'))
            dataset._replace_rows(rows)
        return True

    def _parse_csv(self, raw):
        text = raw.decode('utf-8-sig', errors='replace')
        sample = text[:2048]
        try:
            dialect = csv.Sniffer().sniff(sample)
        except Exception:
            dialect = csv.excel
        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
        return [dict(row) for row in reader]

    def _parse_xlsx(self, raw):
        # Parser básico XLSX sin dependencias externas. Lee la primera hoja del archivo.
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            shared = []
            if 'xl/sharedStrings.xml' in zf.namelist():
                root = ET.fromstring(zf.read('xl/sharedStrings.xml'))
                ns = {'a': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                for si in root.findall('a:si', ns):
                    texts = [t.text or '' for t in si.findall('.//a:t', ns)]
                    shared.append(''.join(texts))
            sheet_name = 'xl/worksheets/sheet1.xml'
            if sheet_name not in zf.namelist():
                candidates = [n for n in zf.namelist() if n.startswith('xl/worksheets/sheet') and n.endswith('.xml')]
                if not candidates:
                    return []
                sheet_name = candidates[0]
            root = ET.fromstring(zf.read(sheet_name))
            ns = {'a': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            matrix = []
            for row in root.findall('.//a:row', ns):
                values = []
                for cell in row.findall('a:c', ns):
                    cell_type = cell.attrib.get('t')
                    v = cell.find('a:v', ns)
                    value = v.text if v is not None else ''
                    if cell_type == 's' and value:
                        idx = int(value)
                        value = shared[idx] if idx < len(shared) else value
                    values.append(value)
                matrix.append(values)
        if not matrix:
            return []
        headers = [str(h or '').strip() or 'Columna %s' % (i + 1) for i, h in enumerate(matrix[0])]
        rows = []
        for row in matrix[1:]:
            rows.append({headers[i]: row[i] if i < len(row) else '' for i in range(len(headers))})
        return rows

    def _replace_rows(self, rows):
        self.ensure_one()
        self.line_ids.unlink()
        headers = list(rows[0].keys()) if rows else []
        self.headers_json = json.dumps(headers, ensure_ascii=False)
        vals = []
        for index, row in enumerate(rows, start=1):
            vals.append({
                'dataset_id': self.id,
                'row_index': index,
                'values_json': json.dumps(row, ensure_ascii=False),
            })
        if vals:
            self.env['vlf.dashboard.dataset.line'].create(vals)
        self.parsed_at = fields.Datetime.now()

    def get_headers(self):
        self.ensure_one()
        try:
            return json.loads(self.headers_json or '[]')
        except Exception:
            return []

    def get_rows_as_dicts(self):
        self.ensure_one()
        rows = []
        for line in self.line_ids.sorted('row_index'):
            try:
                rows.append(json.loads(line.values_json or '{}'))
            except Exception:
                rows.append({})
        return rows


class VlfDashboardDatasetLine(models.Model):
    _name = 'vlf.dashboard.dataset.line'
    _description = 'Fila de dataset para dashboard'
    _order = 'dataset_id, row_index'

    dataset_id = fields.Many2one('vlf.dashboard.dataset', required=True, ondelete='cascade')
    row_index = fields.Integer(required=True)
    values_json = fields.Text(required=True)
