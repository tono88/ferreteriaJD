# -*- coding: utf-8 -*-
"""Fechas comerciales para reportes de POS: una zona por compañía, no por cajero.

Odoo almacena date_order como UTC naive. La zona comercial se resuelve desde
el contacto de la compañía, o Guatemala si no existe una configuración.
"""
from datetime import datetime, time, timedelta

import pytz

DEFAULT_REPORT_TIMEZONE = "America/Guatemala"


def resolve_report_timezone(company):
    """Evitar que la cuenta de cada usuario cambie el corte de caja."""
    timezone_name = company.partner_id.tz or DEFAULT_REPORT_TIMEZONE
    try:
        pytz.timezone(timezone_name)
    except (pytz.UnknownTimeZoneError, TypeError):
        timezone_name = DEFAULT_REPORT_TIMEZONE
    return timezone_name


def local_report_utc_bounds(date_from, date_to, timezone_name):
    """[medianoche Desde, medianoche después de Hasta) convertido a UTC naive.

    Límite final EXCLUSIVO: incluye registros con microsegundos en 23:59:59.
    El cálculo se hace en horario local para soportar cambios de horario de
    verano en compañías que no usan America/Guatemala.
    """
    local_tz = pytz.timezone(timezone_name)
    start_local = local_tz.localize(
        datetime.combine(date_from, time.min), is_dst=None
    )
    next_day_local = local_tz.localize(
        datetime.combine(date_to + timedelta(days=1), time.min), is_dst=None
    )
    return (
        start_local.astimezone(pytz.UTC).replace(tzinfo=None),
        next_day_local.astimezone(pytz.UTC).replace(tzinfo=None),
    )
