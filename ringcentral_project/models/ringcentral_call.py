# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class RingCentralCall(models.Model):
    _inherit = 'ringcentral.call'

    # Project/Task link
    task_id = fields.Many2one(
        'project.task',
        string='Task',
        index=True,
    )
    project_id = fields.Many2one(
        'project.project',
        string='Project',
        related='task_id.project_id',
        store=True,
    )
    
    # Timesheet
    timesheet_id = fields.Many2one(
        'account.analytic.line',
        string='Timesheet Entry',
    )
    auto_create_timesheet = fields.Boolean(
        string='Auto Create Timesheet',
        default=False,
    )

    def action_create_timesheet(self):
        """Create timesheet entry from call"""
        self.ensure_one()
        
        if not self.task_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Task'),
                    'message': _('Please link this call to a task first'),
                    'type': 'warning',
                },
            }
        
        if self.timesheet_id:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Timesheet'),
                'res_model': 'account.analytic.line',
                'res_id': self.timesheet_id.id,
                'view_mode': 'form',
            }
        
        # Create timesheet
        hours = self.duration / 3600.0
        
        timesheet = self.env['account.analytic.line'].create({
            'name': f'Call with {self.partner_id.name or self.phone_number}',
            'project_id': self.task_id.project_id.id,
            'task_id': self.task_id.id,
            'unit_amount': hours,
            'date': self.start_time.date() if self.start_time else fields.Date.today(),
            'employee_id': self.user_id.employee_id.id if self.user_id.employee_id else False,
        })
        
        self.timesheet_id = timesheet.id
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Timesheet'),
            'res_model': 'account.analytic.line',
            'res_id': timesheet.id,
            'view_mode': 'form',
        }

    def write(self, vals):
        res = super().write(vals)
        
        # Auto-create timesheet when call ends
        if vals.get('state') == 'ended':
            for call in self:
                if call.auto_create_timesheet and call.task_id and not call.timesheet_id:
                    call.action_create_timesheet()
        
        return res
