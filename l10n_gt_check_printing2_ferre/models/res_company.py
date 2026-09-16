from odoo import fields, models

class ResCompany(models.Model):
    _inherit = "res.company"

    # Agregamos nuestras opciones al dropdown de 'Diseño del cheque'
    account_check_printing_layout = fields.Selection(
        selection_add=[
            ("l10n_gt_check_printing2_ferre.check_top", "Cheque GT2 - Top Stub"),
            ("l10n_gt_check_printing2_ferre.check_middle", "Cheque GT2 - Middle Stub"),
            ("l10n_gt_check_printing2_ferre.check_bottom", "Cheque GT2 - Bottom Stub"),
        ],
        ondelete={
            "l10n_gt_check_printing2_ferre.check_top": "set default",
            "l10n_gt_check_printing2_ferre.check_middle": "set default",
            "l10n_gt_check_printing2_ferre.check_bottom": "set default",
        },
    )
