# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Portal Access Settings
    ringcentral_portal_access = fields.Boolean(
        string='RingCentral Portal Access',
        default=False,
        help='Allow this partner to access call/SMS history in portal',
    )
    
    ringcentral_can_view_calls = fields.Boolean(
        string='Can View Calls',
        default=True,
    )
    ringcentral_can_view_recordings = fields.Boolean(
        string='Can View Recordings',
        default=False,
    )
    ringcentral_can_view_voicemail = fields.Boolean(
        string='Can View Voicemails',
        default=True,
    )
    ringcentral_can_view_sms = fields.Boolean(
        string='Can View SMS',
        default=True,
    )
    
    # Communication Preferences
    ringcentral_preferred_contact = fields.Selection([
        ('phone', 'Phone Call'),
        ('sms', 'SMS/Text'),
        ('email', 'Email'),
        ('any', 'Any Method'),
    ], string='Preferred Contact Method', default='any')
    
    ringcentral_do_not_call = fields.Boolean(
        string='Do Not Call',
        default=False,
    )
    ringcentral_do_not_sms = fields.Boolean(
        string='Do Not SMS',
        default=False,
    )
    
    ringcentral_preferred_time = fields.Selection([
        ('any', 'Any Time'),
        ('morning', 'Morning (9am - 12pm)'),
        ('afternoon', 'Afternoon (12pm - 5pm)'),
        ('evening', 'Evening (5pm - 8pm)'),
    ], string='Preferred Call Time', default='any')

    def _get_portal_call_count(self):
        """Get count of calls for portal display"""
        self.ensure_one()
        try:
            Call = self.env['ringcentral.call']
        except Exception:
            return 0

        return Call.search_count([('partner_id', '=', self.id)])

    def _get_portal_sms_count(self):
        """Get count of SMS for portal display"""
        self.ensure_one()
        try:
            SMS = self.env['ringcentral.sms']
        except Exception:
            return 0

        return SMS.search_count([('partner_id', '=', self.id)])

    def _get_portal_voicemail_count(self):
        """Get count of voicemails for portal display"""
        self.ensure_one()
        try:
            Voicemail = self.env['ringcentral.voicemail']
        except Exception:
            return 0

        return Voicemail.search_count([('partner_id', '=', self.id)])

    def _get_portal_recording_count(self):
        """Get count of recordings for portal display"""
        self.ensure_one()
        try:
            Recording = self.env['ringcentral.recording']
        except Exception:
            return 0

        return Recording.search_count([('partner_id', '=', self.id)])
