# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class ProjectTask(models.Model):
    _inherit = 'project.task'

    # Call statistics
    call_ids = fields.One2many(
        'ringcentral.call',
        'task_id',
        string='Calls',
    )
    call_count = fields.Integer(
        string='Calls',
        compute='_compute_call_stats',
    )
    total_call_duration = fields.Float(
        string='Total Call Duration (h)',
        compute='_compute_call_stats',
    )

    @api.depends('call_ids')
    def _compute_call_stats(self):
        for task in self:
            task.call_count = len(task.call_ids)
            task.total_call_duration = sum(
                c.duration / 3600.0 for c in task.call_ids
            )

    def action_view_calls(self):
        """View calls linked to this task"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Task Calls'),
            'res_model': 'ringcentral.call',
            'view_mode': 'tree,form',
            'domain': [('task_id', '=', self.id)],
            'context': {'default_task_id': self.id},
        }

    def action_quick_call(self):
        """Quick call related to this task using RingCentral Embeddable widget"""
        self.ensure_one()
        
        partner = self.partner_id
        if not partner:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('No partner assigned to this task'),
                    'type': 'warning',
                }
            }
        
        phone = partner.phone or partner.mobile
        if not phone:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('No phone number available for this partner'),
                    'type': 'warning',
                }
            }
        
        # Use the RingCentral Embeddable widget for consistent call experience
        return {
            'type': 'ir.actions.client',
            'tag': 'ringcentral_embeddable_call',
            'params': {
                'phone_number': phone,
                'partner_name': partner.name,
                'res_model': 'project.task',
                'res_id': self.id,
            },
        }
