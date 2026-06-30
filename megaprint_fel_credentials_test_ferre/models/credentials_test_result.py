# -*- coding: utf-8 -*-

from odoo import fields, models


class MegaprintFelCredentialsTestResult(models.TransientModel):
    _name = "megaprint.fel.credentials.test.result"
    _description = "Resultado de prueba de credenciales FEL Megaprint"
    _rec_name = "journal_id"

    journal_id = fields.Many2one("account.journal", string="Diario", readonly=True)
    tested_at = fields.Datetime(string="Fecha y hora de prueba", readonly=True)
    status = fields.Selection(
        [
            ("success", "Credenciales aceptadas"),
            ("error", "Error"),
            ("blocked", "Prueba bloqueada"),
        ],
        string="Resultado",
        readonly=True,
    )
    environment = fields.Char(string="Ambiente", readonly=True)
    endpoint = fields.Char(string="Endpoint", readonly=True)

    masked_user = fields.Char(string="Usuario enmascarado", readonly=True)
    user_length_raw = fields.Integer(string="Longitud original del usuario", readonly=True)
    user_length_clean = fields.Integer(string="Longitud enviada del usuario", readonly=True)
    api_key_length_raw = fields.Integer(string="Longitud original de API key", readonly=True)
    api_key_length_clean = fields.Integer(string="Longitud enviada de API key", readonly=True)
    user_has_edge_spaces = fields.Boolean(
        string="Usuario tenía espacios al inicio/final", readonly=True
    )
    api_key_has_edge_spaces = fields.Boolean(
        string="API key tenía espacios al inicio/final", readonly=True
    )
    user_sha256_partial = fields.Char(
        string="Huella parcial SHA-256 del usuario enviado", readonly=True
    )
    api_key_sha256_partial = fields.Char(
        string="Huella parcial SHA-256 de la API key enviada", readonly=True
    )

    http_status = fields.Integer(string="Código HTTP", readonly=True)
    functional_code = fields.Char(string="Código funcional", readonly=True)
    functional_description = fields.Text(string="Descripción", readonly=True)
    token_received = fields.Boolean(string="Token recibido", readonly=True)
    token_length = fields.Integer(string="Longitud del token", readonly=True)
    token_expiration = fields.Char(string="Vigencia informada", readonly=True)
    duration_ms = fields.Integer(string="Duración de la llamada (ms)", readonly=True)
