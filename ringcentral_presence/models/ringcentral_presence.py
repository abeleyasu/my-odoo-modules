# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class RingCentralPresence(models.Model):
    _name = 'ringcentral.presence'
    _description = 'RingCentral Presence Status'
    _order = 'user_id'

    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        ondelete='cascade',
        index=True,
    )
    
    # Current Status
    presence_status = fields.Selection([
        ('available', 'Available'),
        ('busy', 'Busy'),
        ('dnd', 'Do Not Disturb'),
        ('offline', 'Offline'),
        ('away', 'Away'),
    ], string='Status', default='offline')
    
    user_status = fields.Selection([
        ('available', 'Available'),
        ('busy', 'Busy'),
        ('dnd', 'Do Not Disturb'),
    ], string='User Status', help='Status set by user preference')
    
    dnd_status = fields.Selection([
        ('takeAllCalls', 'Take All Calls'),
        ('doNotAcceptAnyCalls', 'Do Not Accept Calls'),
        ('doNotAcceptDepartmentCalls', 'Do Not Accept Department Calls'),
        ('takeDepartmentCallsOnly', 'Department Calls Only'),
    ], string='DND Status', default='takeAllCalls')
    
    # Activity Status
    telephony_status = fields.Selection([
        ('noCall', 'No Call'),
        ('callConnected', 'On Call'),
        ('ringing', 'Ringing'),
        ('onHold', 'On Hold'),
        ('parkedCall', 'Parked'),
    ], string='Phone Status', default='noCall')
    
    meeting_status = fields.Selection([
        ('free', 'Free'),
        ('inMeeting', 'In Meeting'),
    ], string='Meeting Status', default='free')
    
    # Display
    status_message = fields.Char(string='Status Message')
    color = fields.Char(compute='_compute_color')
    
    # Timestamps
    last_update = fields.Datetime(
        string='Last Update',
        default=fields.Datetime.now,
    )
    
    # Extension Info
    extension_id = fields.Char(string='Extension ID')

    @api.depends('presence_status')
    def _compute_color(self):
        color_map = {
            'available': '#28a745',  # Green
            'busy': '#ffc107',       # Yellow
            'dnd': '#dc3545',        # Red
            'offline': '#6c757d',    # Gray
            'away': '#fd7e14',       # Orange
        }
        for rec in self:
            rec.color = color_map.get(rec.presence_status, '#6c757d')

    def action_set_available(self):
        """Set status to available"""
        self._set_presence_status('available')

    def action_set_busy(self):
        """Set status to busy"""
        self._set_presence_status('busy')

    def action_set_dnd(self):
        """Set status to Do Not Disturb"""
        self._set_presence_status('dnd')

    def action_set_away(self):
        """Set status to away"""
        self._set_presence_status('away')

    def _set_presence_status(self, status):
        """Update presence status in RingCentral"""
        self.ensure_one()
        
        try:
            rc_api = self.env['ringcentral.api'].sudo()
            
            # Map status to RingCentral values
            rc_status_map = {
                'available': 'Available',
                'busy': 'Busy',
                'dnd': 'DoNotDisturb',
                'away': 'Away',
            }
            
            dnd_map = {
                'available': 'TakeAllCalls',
                'busy': 'TakeAllCalls',
                'dnd': 'DoNotAcceptAnyCalls',
                'away': 'TakeAllCalls',
            }
            
            result = rc_api.set_presence(
                presence_status=rc_status_map.get(status, 'Available'),
                extension_id=self.extension_id or self.user_id.rc_extension_id,
            )
            
            self.write({
                'presence_status': status,
                'user_status': status if status in ('available', 'busy', 'dnd') else 'available',
                'dnd_status': dnd_map.get(status),
                'last_update': fields.Datetime.now(),
            })
            
            # Notify other users
            self._broadcast_presence_update()
            
        except Exception as e:
            _logger.error(f'Failed to set presence: {e}')
            raise UserError(_('Failed to update presence status: %s') % str(e))

    def _broadcast_presence_update(self):
        """Broadcast presence update via bus"""
        self.ensure_one()
        
        self.env['bus.bus']._sendmany([
            (channel, 'ringcentral_presence', {
                'user_id': self.user_id.id,
                'status': self.presence_status,
                'color': self.color,
                'message': self.status_message,
            })
            for channel in ['ringcentral_presence_channel']
        ])

    @api.model
    def process_presence_webhook(self, data):
        """Process presence webhook from RingCentral"""
        extension_id = data.get('extensionId')
        
        if not extension_id:
            return
        
        # Find user by extension
        user = self.env['res.users'].search([
            ('rc_extension_id', '=', str(extension_id))
        ], limit=1)
        
        if not user:
            return
        
        presence = self.search([('user_id', '=', user.id)], limit=1)
        if not presence:
            presence = self.create({'user_id': user.id, 'extension_id': str(extension_id)})
        
        # Map RingCentral status to local status
        status_map = {
            'Available': 'available',
            'Busy': 'busy',
            'DoNotDisturb': 'dnd',
            'Offline': 'offline',
            'Away': 'away',
        }
        
        telephony_map = {
            'NoCall': 'noCall',
            'CallConnected': 'callConnected',
            'Ringing': 'ringing',
            'OnHold': 'onHold',
            'ParkedCall': 'parkedCall',
        }
        
        vals = {
            'presence_status': status_map.get(data.get('presenceStatus'), 'offline'),
            'user_status': status_map.get(data.get('userStatus'), 'available'),
            'telephony_status': telephony_map.get(data.get('telephonyStatus'), 'noCall'),
            'dnd_status': data.get('dndStatus', 'takeAllCalls'),
            'status_message': data.get('message'),
            'last_update': fields.Datetime.now(),
        }
        
        # Set overall status based on telephony
        if vals['telephony_status'] in ('callConnected', 'ringing', 'onHold'):
            vals['presence_status'] = 'busy'
        
        presence.write(vals)
        presence._broadcast_presence_update()
        
        return presence

    @api.model
    def _cron_sync_presence(self):
        """Sync presence status for all users"""
        users = self.env['res.users'].search([
            ('rc_extension_id', '!=', False)
        ])
        
        rc_api = self.env['ringcentral.api'].sudo()
        
        for user in users:
            try:
                result = rc_api.get_presence(user.rc_extension_id)
                self.process_presence_webhook(result)
            except Exception as e:
                _logger.error(f'Failed to sync presence for {user.name}: {e}')

    @api.model
    def get_all_presence(self):
        """Get presence status for all users (for widget)
        
        Uses sudo() to bypass access rights since this is called from the
        systray widget for all users, not just RingCentral users.
        Returns empty list if user doesn't have basic access.
        """
        try:
            # Use sudo to allow all users to see presence status in systray
            presences = self.sudo().search([])
            return [{
                'user_id': p.user_id.id,
                'user_name': p.user_id.name,
                'status': p.presence_status,
                'telephony_status': p.telephony_status,
                'color': p.color,
                'message': p.status_message,
            } for p in presences]
        except Exception as e:
            _logger.warning(f'Failed to get presence status: {e}')
            return []
