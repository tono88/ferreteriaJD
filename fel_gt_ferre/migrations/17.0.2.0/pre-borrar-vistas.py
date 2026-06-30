import logging
from odoo.upgrade import util

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    util.records.remove_view(cr, xml_id="fel_gt_ferre.invoice_form_fel_gt")
    util.records.remove_view(cr, xml_id="fel_gt_ferre.journal_form_fel_gt")
    util.records.remove_view(cr, xml_id="fel_gt_ferre.view_tax_form_fel_gt")
    util.records.remove_view(cr, xml_id="fel_gt_ferre.view_partner_form_fel_gt")
    util.records.remove_view(cr, xml_id="fel_gt_ferre.view_company_form_fel_gt")
    _logger.info("Vistas viejas borradas")
