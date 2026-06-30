# -*- coding: utf-8 -*-
from odoo import models, _

from ..models.preset_registry import VlfDashboardPresetRegistry


class VlfDashboardUpdatePresetsWizard(models.TransientModel):
    _name = 'vlf.dashboard.update.presets.wizard'
    _description = 'Actualizar dashboards predeterminados'

    def action_update_presets(self):
        result = VlfDashboardPresetRegistry(self.env).apply_presets()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Dashboards actualizados'),
                'message': _('Se actualizaron %(dashboards)s dashboards a la versión %(version)s.', **result),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
