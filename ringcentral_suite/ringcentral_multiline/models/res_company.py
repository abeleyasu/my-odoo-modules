# -*- coding: utf-8 -*-
"""
Extend res.company with additional RingCentral multi-line settings.

Adds:
- Multi-line configuration options
- Sync settings
- Default behaviors
"""

from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    """Extend company with RingCentral multi-line settings."""
    
    _inherit = 'res.company'
    
    # ===========================
    # Multi-line Settings
    # ===========================
    
    ringcentral_multiline_enabled = fields.Boolean(
        string='Multi-line Enabled',
        default=True,
        help='Enable multi-line phone number configuration per app/department'
    )
    
    ringcentral_auto_sync_enabled = fields.Boolean(
        string='Auto Sync Enabled',
        default=True,
        help='Automatically sync extensions, phone numbers, and queues from RingCentral'
    )
    
    ringcentral_sync_interval_hours = fields.Integer(
        string='Sync Interval (Hours)',
        default=6,
        help='How often to sync data from RingCentral (0 = manual only)'
    )
    
    ringcentral_last_full_sync = fields.Datetime(
        string='Last Full Sync',
        readonly=True,
        help='Timestamp of last complete sync'
    )
    
    # ===========================
    # Default Behaviors
    # ===========================
    
    ringcentral_allow_user_caller_id = fields.Boolean(
        string='Allow User Caller ID Selection',
        default=True,
        help='Allow users to select their own caller ID in the widget'
    )
    
    ringcentral_enable_from_number_setting = fields.Boolean(
        string='Show From Number in Widget',
        default=True,
        help='Display the from number selector in RingCentral widget'
    )
    
    ringcentral_context_aware_routing = fields.Boolean(
        string='Context-Aware Routing',
        default=True,
        help='Automatically select caller ID based on current Odoo app'
    )
    
    # ===========================
    # Fallback Configuration
    # ===========================
    
    ringcentral_fallback_number_id = fields.Many2one(
        'ringcentral.phone.number',
        string='Fallback Phone Number',
        ondelete='set null',
        domain="[('can_be_caller_id', '=', True), ('company_id', '=', id)]",
        help='Default fallback number when no app-specific number is configured'
    )
    
    ringcentral_main_number_id = fields.Many2one(
        'ringcentral.phone.number',
        string='Main Company Number',
        ondelete='set null',
        domain="[('usage_type', '=', 'MainCompanyNumber'), ('company_id', '=', id)]",
        help='Main company phone number from RingCentral'
    )
    
    # ===========================
    # Statistics
    # ===========================
    
    ringcentral_extension_count = fields.Integer(
        string='Total Extensions',
        compute='_compute_ringcentral_stats',
    )
    
    ringcentral_phone_number_count = fields.Integer(
        string='Total Phone Numbers',
        compute='_compute_ringcentral_stats',
    )
    
    ringcentral_call_queue_count = fields.Integer(
        string='Total Call Queues',
        compute='_compute_ringcentral_stats',
    )
    
    ringcentral_app_config_count = fields.Integer(
        string='App Configurations',
        compute='_compute_ringcentral_stats',
    )
    
    # ===========================
    # Computed Methods
    # ===========================
    
    def _compute_ringcentral_stats(self):
        for company in self:
            company.ringcentral_extension_count = self.env['ringcentral.extension'].search_count([
                ('company_id', '=', company.id)
            ])
            company.ringcentral_phone_number_count = self.env['ringcentral.phone.number'].search_count([
                ('company_id', '=', company.id)
            ])
            company.ringcentral_call_queue_count = self.env['ringcentral.call.queue'].search_count([
                ('company_id', '=', company.id)
            ])
            company.ringcentral_app_config_count = self.env['ringcentral.app.config'].search_count([
                ('company_id', '=', company.id)
            ])
    
    # ===========================
    # Business Methods
    # ===========================
    
    def action_sync_ringcentral_data(self):
        """Trigger a full sync of RingCentral data."""
        self.ensure_one()
        
        SyncService = self.env['ringcentral.sync.service']
        results = SyncService.sync_all(self)
        
        self.ringcentral_last_full_sync = fields.Datetime.now()
        
        message = _(
            "Sync Complete:\n"
            "- Extensions: %(ext_created)d created, %(ext_updated)d updated\n"
            "- Phone Numbers: %(phone_created)d created, %(phone_updated)d updated\n"
            "- Call Queues: %(queue_created)d created, %(queue_updated)d updated\n"
            "- Total Time: %(time).2f seconds"
        ) % {
            'ext_created': results['extensions'].get('created', 0),
            'ext_updated': results['extensions'].get('updated', 0),
            'phone_created': results['phone_numbers'].get('created', 0),
            'phone_updated': results['phone_numbers'].get('updated', 0),
            'queue_created': results['call_queues'].get('created', 0),
            'queue_updated': results['call_queues'].get('updated', 0),
            'time': results.get('total_time_seconds', 0),
        }
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('RingCentral Sync'),
                'message': message,
                'type': 'success',
                'sticky': True,
            }
        }
    
    def action_auto_link_users(self):
        """Auto-link users to extensions by email."""
        self.ensure_one()
        
        results = self.env['res.users'].auto_link_extensions_by_email(self)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Auto-Link Complete'),
                'message': _("Linked %(linked)d users, %(no_match)d without matches.") % {
                    'linked': results['linked'],
                    'no_match': results['no_match'],
                },
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_auto_link_departments(self):
        """Auto-link departments to call queues by name."""
        self.ensure_one()
        
        results = self.env['hr.department'].auto_link_queues_by_name(self)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Auto-Link Complete'),
                'message': _("Linked %(linked)d departments, %(no_match)d without matches.") % {
                    'linked': results['linked'],
                    'no_match': results['no_match'],
                },
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_view_extensions(self):
        """View all extensions for this company."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('RingCentral Extensions'),
            'res_model': 'ringcentral.extension',
            'view_mode': 'tree,form',
            'domain': [('company_id', '=', self.id)],
        }
    
    def action_view_phone_numbers(self):
        """View all phone numbers for this company."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('RingCentral Phone Numbers'),
            'res_model': 'ringcentral.phone.number',
            'view_mode': 'tree,form',
            'domain': [('company_id', '=', self.id)],
        }
    
    def action_view_call_queues(self):
        """View all call queues for this company."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('RingCentral Call Queues'),
            'res_model': 'ringcentral.call.queue',
            'view_mode': 'tree,form',
            'domain': [('company_id', '=', self.id)],
        }
    
    def action_view_app_configs(self):
        """View app configurations for this company."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('App Phone Configurations'),
            'res_model': 'ringcentral.app.config',
            'view_mode': 'tree,form',
            'domain': [('company_id', '=', self.id)],
        }
    
    def action_quick_setup_wizard(self):
        """Open the quick setup wizard."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Quick App Configuration'),
            'res_model': 'ringcentral.app.config.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_company_id': self.id,
            },
        }
