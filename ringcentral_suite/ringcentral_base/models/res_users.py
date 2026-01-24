# -*- coding: utf-8 -*-
"""
RingCentral User Extension
==========================

Extension of res.users for per-user RingCentral settings.
"""

from odoo import api, fields, models


class ResUsers(models.Model):
    """User extension for RingCentral settings"""
    
    _inherit = 'res.users'
    
    # ===========================
    # User Extension Info
    # ===========================
    
    ringcentral_extension_id = fields.Char(
        string='RingCentral Extension ID',
        help='User\'s RingCentral extension ID'
    )
    
    # Alias for backward compatibility with other modules
    rc_extension_id = fields.Char(
        string='RC Extension ID',
        related='ringcentral_extension_id',
        store=True,
        help='Alias for ringcentral_extension_id'
    )
    
    ringcentral_extension_number = fields.Char(
        string='Extension Number',
        help='User\'s extension number'
    )
    
    ringcentral_direct_number = fields.Char(
        string='Direct Number',
        help='User\'s direct phone number'
    )
    
    # ===========================
    # Presence
    # ===========================
    
    ringcentral_presence_status = fields.Selection([
        ('Available', 'Available'),
        ('Busy', 'Busy'),
        ('DoNotDisturb', 'Do Not Disturb'),
        ('Offline', 'Offline'),
    ], string='Presence Status',
       default='Available',
       help='Current RingCentral presence status')
    
    ringcentral_telephony_status = fields.Selection([
        ('NoCall', 'No Call'),
        ('Ringing', 'Ringing'),
        ('OnHold', 'On Hold'),
        ('CallConnected', 'On Call'),
    ], string='Telephony Status',
       default='NoCall',
       help='Current call status')
    
    ringcentral_dnd_status = fields.Boolean(
        string='Do Not Disturb',
        default=False,
        help='Do Not Disturb mode enabled'
    )
    
    # ===========================
    # User Preferences
    # ===========================
    
    ringcentral_softphone_enabled = fields.Boolean(
        string='Enable Softphone',
        default=False,
        help='Enable WebRTC softphone in browser'
    )
    
    ringcentral_click_to_dial_mode = fields.Selection([
        ('ringout', 'RingOut (Callback)'),
        ('webrtc', 'WebRTC (Browser)'),
    ], string='Click-to-Dial Mode',
       default='ringout',
       help='Preferred click-to-dial method')
    
    ringcentral_auto_answer = fields.Boolean(
        string='Auto-Answer Calls',
        default=False,
        help='Automatically answer incoming calls'
    )
    
    ringcentral_show_popup = fields.Boolean(
        string='Show Incoming Call Popup',
        default=True,
        help='Show popup notification for incoming calls'
    )
    
    # ===========================
    # Methods
    # ===========================
    
    def action_sync_ringcentral_extension(self):
        """Sync user's RingCentral extension info"""
        self.ensure_one()
        
        api = self.env['ringcentral.api']
        
        try:
            if self.ringcentral_extension_id:
                ext_info = api.get_extension_info(self.ringcentral_extension_id)
            else:
                ext_info = api.get_extension_info('~')
            
            self.write({
                'ringcentral_extension_id': str(ext_info.get('id')),
                'ringcentral_extension_number': ext_info.get('extensionNumber'),
            })
            
            # Get phone numbers
            phone_info = api.get_phone_numbers()
            direct_numbers = [
                p.get('phoneNumber') 
                for p in phone_info.get('records', [])
                if p.get('usageType') == 'DirectNumber'
            ]
            
            if direct_numbers:
                self.write({'ringcentral_direct_number': direct_numbers[0]})
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Extension Synced',
                    'message': f'Extension {self.ringcentral_extension_number} synced successfully.',
                    'type': 'success',
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Sync Failed',
                    'message': str(e),
                    'type': 'danger',
                }
            }
    
    def action_set_presence(self, status=None):
        """Set user's RingCentral presence status"""
        self.ensure_one()
        
        # Get status from parameter or context
        if status is None:
            status = self.env.context.get('default_status', 'available')
        
        api = self.env['ringcentral.api']
        
        try:
            api.set_presence(status, self.ringcentral_extension_id or '~')
            self.write({'ringcentral_presence_status': status})
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': str(e),
                    'type': 'danger',
                }
            }
    
    @api.model
    def _get_users_by_extension(self, extension_id):
        """Find user by RingCentral extension ID"""
        return self.search([
            ('ringcentral_extension_id', '=', str(extension_id))
        ], limit=1)
