# -*- coding: utf-8 -*-
"""
RingCentral Configuration Settings
==================================

Extension of res.config.settings for RingCentral configuration.
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    """RingCentral Configuration Settings"""
    
    _inherit = 'res.config.settings'
    
    # ===========================
    # Enable/Disable
    # ===========================
    
    ringcentral_enabled = fields.Boolean(
        related='company_id.ringcentral_enabled',
        readonly=False,
        string='Enable RingCentral Integration'
    )
    
    # ===========================
    # Authentication - JWT
    # ===========================
    
    ringcentral_client_id = fields.Char(
        related='company_id.ringcentral_client_id',
        readonly=False,
        string='Client ID',
        help='RingCentral App Client ID from developer portal'
    )
    
    ringcentral_client_secret = fields.Char(
        related='company_id.ringcentral_client_secret',
        readonly=False,
        string='Client Secret',
        help='RingCentral App Client Secret'
    )
    
    ringcentral_jwt_token = fields.Char(
        related='company_id.ringcentral_jwt_token',
        readonly=False,
        string='JWT Token',
        help='JWT credential for server-to-server authentication (recommended)'
    )
    
    # ===========================
    # Authentication - OAuth (Alternative)
    # ===========================
    
    ringcentral_username = fields.Char(
        related='company_id.ringcentral_username',
        readonly=False,
        string='Username',
        help='RingCentral account username (phone number)'
    )
    
    ringcentral_password = fields.Char(
        related='company_id.ringcentral_password',
        readonly=False,
        string='Password',
        help='RingCentral account password'
    )
    
    ringcentral_extension = fields.Char(
        related='company_id.ringcentral_extension',
        readonly=False,
        string='Extension',
        help='RingCentral extension number (optional)'
    )
    
    # ===========================
    # Server Configuration
    # ===========================
    
    ringcentral_server_url = fields.Selection(
        related='company_id.ringcentral_server_url_selection',
        readonly=False,
        string='Environment',
        help='RingCentral API environment'
    )
    
    ringcentral_webhook_url = fields.Char(
        related='company_id.ringcentral_webhook_url',
        readonly=False,
        string='Webhook URL',
        help='URL for RingCentral to send event notifications'
    )
    
    ringcentral_webhook_secret = fields.Char(
        related='company_id.ringcentral_webhook_secret',
        readonly=False,
        string='Webhook Secret',
        help='Secret for validating webhook signatures'
    )
    
    # ===========================
    # Default Settings
    # ===========================
    
    ringcentral_default_caller_id = fields.Char(
        related='company_id.ringcentral_default_caller_id',
        readonly=False,
        string='Default Caller ID',
        help='Default outbound caller ID number'
    )
    
    ringcentral_auto_record_calls = fields.Boolean(
        related='company_id.ringcentral_auto_record_calls',
        readonly=False,
        string='Auto-Record Calls',
        help='Automatically record all outbound calls'
    )
    
    ringcentral_call_prompt = fields.Boolean(
        related='company_id.ringcentral_call_prompt',
        readonly=False,
        string='Play Connection Prompt',
        help='Play prompt when RingOut call connects'
    )
    
    # ===========================
    # Health Status (Read-only)
    # ===========================
    
    ringcentral_health_status = fields.Selection(
        related='company_id.ringcentral_health_status',
        readonly=True,
        string='Connection Status'
    )
    
    ringcentral_last_health_check = fields.Datetime(
        related='company_id.ringcentral_last_health_check',
        readonly=True,
        string='Last Health Check'
    )
    
    ringcentral_health_latency = fields.Float(
        related='company_id.ringcentral_health_latency',
        readonly=True,
        string='API Latency (ms)'
    )
    
    # ===========================
    # Actions
    # ===========================
    
    def action_test_connection(self):
        """Test RingCentral connection"""
        self.ensure_one()
        
        api = self.env['ringcentral.api']
        result = api.health_check(self.company_id)
        
        if result['status'] == 'healthy':
            message = _(
                "Connection successful!\n\n"
                "Account: %(account_id)s\n"
                "Status: %(status)s\n"
                "Plan: %(plan)s\n"
                "Latency: %(latency)s ms"
            ) % {
                'account_id': result['details'].get('account_id', 'N/A'),
                'status': result['details'].get('account_status', 'N/A'),
                'plan': result['details'].get('service_plan', 'N/A'),
                'latency': result['latency_ms'],
            }
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('RingCentral Connection Test'),
                    'message': message,
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            raise UserError(_(
                "Connection failed!\n\n"
                "Error: %s"
            ) % result['details'].get('error', 'Unknown error'))
    
    def action_setup_webhooks(self):
        """Setup RingCentral webhooks"""
        self.ensure_one()
        
        if not self.ringcentral_webhook_url:
            raise UserError(_("Please configure the Webhook URL first."))
        
        api = self.env['ringcentral.api']
        
        # Event filters for all subscriptions
        event_filters = [
            '/restapi/v1.0/account/~/extension/~/telephony/sessions',  # Call events
            '/restapi/v1.0/account/~/extension/~/message-store',  # SMS/Voicemail
            '/restapi/v1.0/account/~/extension/~/presence',  # Presence changes
            '/restapi/v1.0/account/~/extension/~/voicemail',  # Voicemail
        ]
        
        try:
            result = api.create_subscription(
                event_filters=event_filters,
                delivery_url=self.ringcentral_webhook_url,
                company=self.company_id
            )
            
            self.company_id.sudo().write({
                'ringcentral_subscription_id': result.get('id'),
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Webhooks Setup'),
                    'message': _('Webhook subscription created successfully!'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(_("Failed to setup webhooks: %s") % str(e))
    
    def action_view_api_logs(self):
        """Open API logs view"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('RingCentral API Logs'),
            'res_model': 'ringcentral.api.log',
            'view_mode': 'tree,form',
            'domain': [('company_id', '=', self.company_id.id)],
            'context': {'default_company_id': self.company_id.id},
        }
    
    def action_sync_phone_numbers(self):
        """Sync phone numbers from RingCentral"""
        self.ensure_one()
        
        api = self.env['ringcentral.api']
        
        try:
            result = api.get_phone_numbers(company=self.company_id)
            numbers = result.get('records', [])
            
            # Store phone numbers for selection
            phone_list = []
            for num in numbers:
                phone_list.append({
                    'number': num.get('phoneNumber'),
                    'type': num.get('type'),
                    'usage_type': num.get('usageType'),
                })
            
            self.company_id.sudo().write({
                'ringcentral_phone_numbers': str(phone_list),
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Phone Numbers Synced'),
                    'message': _('Found %d phone numbers.') % len(numbers),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(_("Failed to sync phone numbers: %s") % str(e))
