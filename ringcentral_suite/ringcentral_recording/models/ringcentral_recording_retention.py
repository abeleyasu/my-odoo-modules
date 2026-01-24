# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import timedelta


class RingCentralRecordingRetention(models.Model):
    _name = 'ringcentral.recording.retention'
    _description = 'Recording Retention Policy'
    _order = 'name'

    name = fields.Char(string='Policy Name', required=True)
    active = fields.Boolean(default=True)
    
    # Retention Period
    retention_days = fields.Integer(
        string='Retention Period (days)',
        default=90,
        help='Number of days to retain recordings',
    )
    
    # Scope
    apply_to = fields.Selection([
        ('all', 'All Recordings'),
        ('inbound', 'Inbound Calls Only'),
        ('outbound', 'Outbound Calls Only'),
        ('automatic', 'Automatic Recordings'),
        ('on_demand', 'On-Demand Recordings'),
    ], string='Apply To', default='all')
    
    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
    
    # Automatic Actions
    auto_archive = fields.Boolean(
        string='Auto Archive',
        default=True,
        help='Automatically archive recordings when retention expires',
    )
    auto_delete = fields.Boolean(
        string='Auto Delete',
        default=False,
        help='Automatically delete recordings when retention expires',
    )
    
    # Compliance
    compliance_type = fields.Selection([
        ('standard', 'Standard'),
        ('gdpr', 'GDPR'),
        ('hipaa', 'HIPAA'),
        ('pci', 'PCI DSS'),
        ('custom', 'Custom'),
    ], string='Compliance Type', default='standard')
    
    notes = fields.Text(string='Notes')
    
    recording_count = fields.Integer(
        compute='_compute_recording_count',
        string='Recordings',
    )

    def _compute_recording_count(self):
        for policy in self:
            policy.recording_count = self.env['ringcentral.recording'].search_count([
                ('retention_policy_id', '=', policy.id)
            ])

    def action_view_recordings(self):
        """View recordings with this policy"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Recordings - {self.name}',
            'res_model': 'ringcentral.recording',
            'view_mode': 'tree,form',
            'domain': [('retention_policy_id', '=', self.id)],
        }

    def calculate_expiry_date(self):
        """Calculate expiry date based on retention policy"""
        self.ensure_one()
        return fields.Date.today() + timedelta(days=self.retention_days)
