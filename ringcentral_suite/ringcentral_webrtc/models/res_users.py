# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    # WebRTC Settings
    ringcentral_webrtc_enabled = fields.Boolean(
        string='WebRTC Softphone Enabled',
        default=True,
    )
    ringcentral_auto_answer = fields.Boolean(
        string='Auto Answer',
        default=False,
        help='Automatically answer incoming calls',
    )
    ringcentral_auto_answer_delay = fields.Integer(
        string='Auto Answer Delay (seconds)',
        default=3,
    )
    ringcentral_ring_sound = fields.Selection([
        ('default', 'Default'),
        ('classic', 'Classic'),
        ('digital', 'Digital'),
        ('subtle', 'Subtle'),
        ('none', 'No Sound'),
    ], string='Ring Sound', default='default')
    
    # Audio Device Preferences
    ringcentral_input_device = fields.Char(string='Input Device ID')
    ringcentral_output_device = fields.Char(string='Output Device ID')
    ringcentral_ringtone_device = fields.Char(string='Ringtone Device ID')
    
    # Softphone Position
    ringcentral_softphone_position = fields.Selection([
        ('bottom_right', 'Bottom Right'),
        ('bottom_left', 'Bottom Left'),
        ('top_right', 'Top Right'),
        ('top_left', 'Top Left'),
    ], string='Softphone Position', default='bottom_right')

    def get_webrtc_config(self):
        """Get WebRTC configuration for current user"""
        self.ensure_one()
        
        # Check if WebRTC is enabled for this user
        if not self.ringcentral_webrtc_enabled:
            return {'enabled': False, 'error': 'WebRTC not enabled for user'}
        
        # Get company settings
        company = self.company_id or self.env.company
        if not company.ringcentral_enabled:
            return {'enabled': False, 'error': 'RingCentral not enabled for company'}
        
        # Try to get SIP credentials from RingCentral API
        try:
            api = self.env['ringcentral.api'].get_api()
            if not api:
                return {
                    'enabled': True,
                    'auto_answer': self.ringcentral_auto_answer,
                    'auto_answer_delay': self.ringcentral_auto_answer_delay,
                    'ring_sound': self.ringcentral_ring_sound,
                    'position': self.ringcentral_softphone_position,
                    'sip': None,
                    'user_extension': self.ringcentral_extension,
                    'warning': 'RingCentral API not configured',
                }
            
            # Get SIP provision info (for WebRTC)
            sip_info = api.get_sip_provision()
            
            return {
                'enabled': True,
                'auto_answer': self.ringcentral_auto_answer,
                'auto_answer_delay': self.ringcentral_auto_answer_delay,
                'ring_sound': self.ringcentral_ring_sound,
                'position': self.ringcentral_softphone_position,
                'sip': sip_info,
                'user_extension': self.ringcentral_extension,
            }
        except Exception as e:
            _logger.warning(f'Failed to get WebRTC SIP config: {e}')
            return {
                'enabled': True,
                'auto_answer': self.ringcentral_auto_answer,
                'auto_answer_delay': self.ringcentral_auto_answer_delay,
                'ring_sound': self.ringcentral_ring_sound,
                'position': self.ringcentral_softphone_position,
                'sip': None,
                'user_extension': self.ringcentral_extension,
                'warning': str(e),
            }

    def save_audio_devices(self, input_device, output_device, ringtone_device):
        """Save audio device preferences"""
        self.ensure_one()
        self.write({
            'ringcentral_input_device': input_device,
            'ringcentral_output_device': output_device,
            'ringcentral_ringtone_device': ringtone_device,
        })
        return True
