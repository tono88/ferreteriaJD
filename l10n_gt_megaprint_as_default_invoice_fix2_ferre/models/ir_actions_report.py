# -*- coding: utf-8 -*-
import logging

from odoo import api, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

MEGAPRINT_QWEB = "l10n_gt_fel_megaprint_report_ferre.report_fel_invoice"
LEGACY_QWEB = "l10n_gt_fel_megaprint_report.report_fel_invoice"
CANDIDATE_REPORT_XMLIDS = (
    "account.action_report_invoice",
    "account.account_invoices",
    "account.action_report_move",
)


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    @api.model
    def _sync_megaprint_default_invoice_report_ferre(self):
        """Repair stale report actions left by the technical-name migration.

        This method is called from XML data, so it runs both on installation and
        on module upgrade. It uses ORM only and does not touch invoices.
        """
        template = self.env["ir.ui.view"].search(
            [("key", "=", MEGAPRINT_QWEB)], limit=1
        )
        if not template:
            raise UserError(_(
                "No se encontró la plantilla FEL %s. Actualice primero el módulo "
                "l10n_gt_fel_megaprint_report_ferre."
            ) % MEGAPRINT_QWEB)

        legacy_actions = self.search([
            ("model", "=", "account.move"),
            ("report_type", "=", "qweb-pdf"),
            "|",
            ("report_name", "=", LEGACY_QWEB),
            ("report_file", "=", LEGACY_QWEB),
        ])

        primary_action = self.browse()
        for xmlid in CANDIDATE_REPORT_XMLIDS:
            candidate = self.env.ref(xmlid, raise_if_not_found=False)
            if candidate and candidate._name == "ir.actions.report":
                primary_action = candidate
                break

        actions = legacy_actions | primary_action
        if not actions:
            raise UserError(_(
                "No se encontró la acción de reporte de factura que debe usar "
                "el formato FEL Megaprint."
            ))

        actions.write({
            "report_name": MEGAPRINT_QWEB,
            "report_file": MEGAPRINT_QWEB,
            "name": "Factura (Megaprint)",
        })

        template_email = self.env.ref(
            "account.email_template_edi_invoice", raise_if_not_found=False
        )
        if template_email:
            field_name = (
                "report_template"
                if "report_template" in template_email._fields
                else "report_template_id"
                if "report_template_id" in template_email._fields
                else False
            )
            if field_name and primary_action:
                template_email.write({field_name: primary_action.id})

        _logger.info(
            "[FEL_REPORT_SYNC] report actions repaired ids=%s report_name=%s",
            actions.ids,
            MEGAPRINT_QWEB,
        )
        return True
