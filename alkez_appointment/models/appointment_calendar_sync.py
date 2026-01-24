# Copyright 2024 Your Company
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from datetime import datetime, timedelta
import json
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AppointmentCalendarSync(models.Model):
    """External calendar synchronization for appointments"""
    _name = "appointment.calendar.sync"
    _description = "Calendar Synchronization"
    _order = "create_date desc"

    name = fields.Char(string="Name", compute="_compute_name", store=True)
    
    user_id = fields.Many2one(
        'res.users',
        string="User",
        required=True,
        default=lambda self: self.env.user,
        ondelete='cascade'
    )
    
    # Provider
    provider = fields.Selection([
        ('google', 'Google Calendar'),
        ('outlook', 'Microsoft Outlook'),
        ('apple', 'Apple iCloud'),
        ('ical', 'iCal Feed'),
    ], string="Provider", required=True, default='google')
    
    # OAuth Status
    state = fields.Selection([
        ('not_connected', 'Not Connected'),
        ('connected', 'Connected'),
        ('error', 'Error'),
    ], string="Status", default='not_connected')
    
    # OAuth Tokens (encrypted in production)
    access_token = fields.Char(string="Access Token")
    refresh_token = fields.Char(string="Refresh Token")
    token_expires = fields.Datetime(string="Token Expires")
    
    # Sync Settings
    sync_direction = fields.Selection([
        ('both', 'Two-Way Sync'),
        ('to_external', 'Odoo → External'),
        ('from_external', 'External → Odoo'),
    ], string="Sync Direction", default='both')
    
    sync_calendar_id = fields.Char(
        string="External Calendar ID",
        help="ID of the calendar to sync with"
    )
    sync_calendar_name = fields.Char(string="Calendar Name")
    
    # Sync Status
    last_sync = fields.Datetime(string="Last Sync")
    last_sync_status = fields.Selection([
        ('success', 'Success'),
        ('partial', 'Partial'),
        ('failed', 'Failed'),
    ], string="Last Sync Status")
    last_sync_message = fields.Text(string="Last Sync Message")
    
    # Auto-sync
    auto_sync = fields.Boolean(string="Auto Sync", default=True)
    sync_interval = fields.Integer(
        string="Sync Interval (minutes)",
        default=15
    )
    
    # Block external events
    block_external_events = fields.Boolean(
        string="Block External Events",
        default=True,
        help="Consider external calendar events as busy time"
    )

    @api.depends('user_id', 'provider')
    def _compute_name(self):
        providers = dict(self._fields['provider'].selection)
        for record in self:
            provider_name = providers.get(record.provider, record.provider)
            record.name = f"{record.user_id.name} - {provider_name}"

    def action_connect(self):
        """Initiate OAuth connection"""
        self.ensure_one()
        
        if self.provider == 'google':
            return self._connect_google()
        elif self.provider == 'outlook':
            return self._connect_outlook()
        elif self.provider == 'ical':
            return self._connect_ical()
        
        raise UserError(_("Provider not supported"))

    def action_disconnect(self):
        """Disconnect calendar"""
        self.write({
            'state': 'not_connected',
            'access_token': False,
            'refresh_token': False,
            'token_expires': False,
            'sync_calendar_id': False,
        })
        return True

    def action_sync_now(self):
        """Perform immediate sync"""
        self.ensure_one()
        try:
            if self.provider == 'google':
                self._sync_google()
            elif self.provider == 'outlook':
                self._sync_outlook()
            elif self.provider == 'ical':
                self._sync_ical()
            
            self.write({
                'last_sync': fields.Datetime.now(),
                'last_sync_status': 'success',
                'last_sync_message': 'Sync completed successfully',
            })
        except Exception as e:
            _logger.exception("Calendar sync failed")
            self.write({
                'last_sync': fields.Datetime.now(),
                'last_sync_status': 'failed',
                'last_sync_message': str(e),
            })

    def _connect_google(self):
        """Connect to Google Calendar"""
        # Get OAuth credentials from system parameters
        ICP = self.env['ir.config_parameter'].sudo()
        client_id = ICP.get_param('appointment.google_client_id')
        
        if not client_id:
            raise UserError(_(
                "Google Calendar integration not configured. "
                "Please set up OAuth credentials in Settings."
            ))
        
        base_url = ICP.get_param('web.base.url')
        redirect_uri = f"{base_url}/appointment/calendar/google/callback"
        
        # Build OAuth URL
        auth_url = (
            "https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={client_id}&"
            f"redirect_uri={redirect_uri}&"
            "scope=https://www.googleapis.com/auth/calendar&"
            "response_type=code&"
            "access_type=offline&"
            f"state={self.id}"
        )
        
        return {
            'type': 'ir.actions.act_url',
            'url': auth_url,
            'target': 'new',
        }

    def _connect_outlook(self):
        """Connect to Microsoft Outlook Calendar"""
        ICP = self.env['ir.config_parameter'].sudo()
        client_id = ICP.get_param('appointment.outlook_client_id')
        
        if not client_id:
            raise UserError(_(
                "Microsoft Outlook integration not configured. "
                "Please set up OAuth credentials in Settings."
            ))
        
        base_url = ICP.get_param('web.base.url')
        redirect_uri = f"{base_url}/appointment/calendar/outlook/callback"
        
        # Build OAuth URL
        auth_url = (
            "https://login.microsoftonline.com/common/oauth2/v2.0/authorize?"
            f"client_id={client_id}&"
            f"redirect_uri={redirect_uri}&"
            "scope=Calendars.ReadWrite offline_access&"
            "response_type=code&"
            f"state={self.id}"
        )
        
        return {
            'type': 'ir.actions.act_url',
            'url': auth_url,
            'target': 'new',
        }

    def _connect_ical(self):
        """Setup iCal feed connection"""
        # iCal is read-only, just mark as connected
        self.write({
            'state': 'connected',
            'sync_direction': 'from_external',
        })
        return True

    def _sync_google(self):
        """Sync with Google Calendar"""
        if not self.access_token:
            raise UserError(_("Not connected to Google Calendar"))
        
        # Check if token needs refresh
        if self.token_expires and self.token_expires < fields.Datetime.now():
            self._refresh_google_token()
        
        # Implement sync logic here
        # This would involve calling Google Calendar API
        _logger.info("Syncing with Google Calendar for user %s", self.user_id.name)

    def _sync_outlook(self):
        """Sync with Microsoft Outlook"""
        if not self.access_token:
            raise UserError(_("Not connected to Outlook"))
        
        _logger.info("Syncing with Outlook for user %s", self.user_id.name)

    def _sync_ical(self):
        """Sync with iCal feed"""
        if not self.sync_calendar_id:
            raise UserError(_("No iCal URL configured"))
        
        import urllib.request
        try:
            response = urllib.request.urlopen(self.sync_calendar_id)
            ical_data = response.read().decode('utf-8')
            self._parse_ical(ical_data)
        except Exception as e:
            raise UserError(_("Failed to fetch iCal feed: %s") % str(e))

    def _parse_ical(self, ical_data):
        """Parse iCal data and create/update events"""
        # Basic iCal parsing - in production use icalendar library
        _logger.info("Parsing iCal data for user %s", self.user_id.name)

    def _refresh_google_token(self):
        """Refresh Google OAuth token"""
        ICP = self.env['ir.config_parameter'].sudo()
        client_id = ICP.get_param('appointment.google_client_id')
        client_secret = ICP.get_param('appointment.google_client_secret')
        
        if not client_secret:
            raise UserError(_("Google client secret not configured"))
        
        import urllib.request
        import urllib.parse
        
        data = urllib.parse.urlencode({
            'client_id': client_id,
            'client_secret': client_secret,
            'refresh_token': self.refresh_token,
            'grant_type': 'refresh_token',
        }).encode()
        
        req = urllib.request.Request(
            'https://oauth2.googleapis.com/token',
            data=data,
            method='POST'
        )
        
        response = urllib.request.urlopen(req)
        token_data = json.loads(response.read().decode())
        
        self.write({
            'access_token': token_data['access_token'],
            'token_expires': fields.Datetime.now() + timedelta(seconds=token_data['expires_in']),
        })

    def get_external_busy_times(self, start_date, end_date):
        """Get busy times from external calendar"""
        self.ensure_one()
        busy_times = []
        
        if self.state != 'connected' or not self.block_external_events:
            return busy_times
        
        # Would query external calendar for events
        # Return list of (start, end) tuples
        return busy_times

    @api.model
    def _cron_sync_calendars(self):
        """Cron job to sync all calendars"""
        syncs = self.search([
            ('state', '=', 'connected'),
            ('auto_sync', '=', True),
        ])
        
        for sync in syncs:
            try:
                sync.action_sync_now()
            except Exception:
                _logger.exception("Auto-sync failed for %s", sync.name)
