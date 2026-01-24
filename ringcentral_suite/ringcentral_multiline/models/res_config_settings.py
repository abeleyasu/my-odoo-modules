# -*- coding: utf-8 -*-
"""
Extend res.config.settings with RingCentral multi-line settings.

Maps company fields to settings form.
"""

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    """Extend settings with RingCentral multi-line options."""
    
    _inherit = 'res.config.settings'
    
    # ===========================
    # Multi-line Settings
    # ===========================
    
    ringcentral_multiline_enabled = fields.Boolean(
        related='company_id.ringcentral_multiline_enabled',
        readonly=False,
        string='Multi-line Enabled',
    )
    
    ringcentral_auto_sync_enabled = fields.Boolean(
        related='company_id.ringcentral_auto_sync_enabled',
        readonly=False,
        string='Auto Sync Enabled',
    )
    
    ringcentral_sync_interval_hours = fields.Integer(
        related='company_id.ringcentral_sync_interval_hours',
        readonly=False,
        string='Sync Interval (Hours)',
    )
    
    # ===========================
    # Default Behaviors
    # ===========================
    
    ringcentral_allow_user_caller_id = fields.Boolean(
        related='company_id.ringcentral_allow_user_caller_id',
        readonly=False,
        string='Allow User Caller ID Selection',
    )
    
    ringcentral_enable_from_number_setting = fields.Boolean(
        related='company_id.ringcentral_enable_from_number_setting',
        readonly=False,
        string='Show From Number in Widget',
    )
    
    ringcentral_context_aware_routing = fields.Boolean(
        related='company_id.ringcentral_context_aware_routing',
        readonly=False,
        string='Context-Aware Routing',
    )
    
    # ===========================
    # Actions
    # ===========================
    
    def action_sync_ringcentral_data(self):
        """Trigger manual sync of all RingCentral data."""
        SyncService = self.env['ringcentral.sync.service']
        return SyncService.sync_all(company=self.company_id)
