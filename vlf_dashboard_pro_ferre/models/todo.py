# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class VlfDashboardTodo(models.Model):
    _name = 'vlf.dashboard.todo'
    _description = 'To-do de dashboard'
    _order = 'state, priority desc, deadline asc, id desc'

    name = fields.Char(required=True)
    dashboard_id = fields.Many2one('vlf.dashboard', required=True, ondelete='cascade')
    item_id = fields.Many2one('vlf.dashboard.item', ondelete='set null')
    state = fields.Selection([
        ('open', 'Abierto'),
        ('done', 'Hecho'),
        ('cancel', 'Cancelado'),
    ], default='open', required=True)
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Importante'),
        ('2', 'Urgente'),
    ], default='0')
    deadline = fields.Date()
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    note = fields.Text()

    def action_done(self):
        self.write({'state': 'done'})

    def action_open(self):
        self.write({'state': 'open'})
