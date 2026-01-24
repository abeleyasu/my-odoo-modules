# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class RingCentralMeeting(models.Model):
    _name = 'ringcentral.meeting'
    _description = 'RingCentral Video Meeting'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'scheduled_start desc'

    # RingCentral Info
    ringcentral_meeting_id = fields.Char(
        string='RingCentral Meeting ID',
        index=True,
        readonly=True,
    )
    bridge_id = fields.Char(string='Bridge ID')
    
    # Basic Info
    name = fields.Char(string='Meeting Name', required=True)
    meeting_type = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('instant', 'Instant'),
        ('recurring', 'Recurring'),
    ], string='Type', default='scheduled', required=True)
    
    # Scheduling
    scheduled_start = fields.Datetime(
        string='Start Time',
        required=True,
        default=lambda self: fields.Datetime.now() + timedelta(hours=1),
    )
    scheduled_end = fields.Datetime(
        string='End Time',
        compute='_compute_scheduled_end',
        store=True,
        readonly=False,
    )
    duration = fields.Integer(
        string='Duration (minutes)',
        default=60,
    )
    timezone = fields.Char(string='Timezone', default='UTC')
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('started', 'In Progress'),
        ('ended', 'Ended'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    actual_start = fields.Datetime(string='Actual Start')
    actual_end = fields.Datetime(string='Actual End')
    
    # Join Info
    join_url = fields.Char(string='Join URL', readonly=True)
    host_url = fields.Char(string='Host URL', readonly=True)
    password = fields.Char(string='Meeting Password')
    dial_in_number = fields.Char(string='Dial-in Number')
    
    # Settings
    allow_join_before_host = fields.Boolean(
        string='Allow Join Before Host',
        default=False,
    )
    mute_participants_on_entry = fields.Boolean(
        string='Mute on Entry',
        default=True,
    )
    enable_waiting_room = fields.Boolean(
        string='Enable Waiting Room',
        default=True,
    )
    enable_recording = fields.Boolean(
        string='Enable Recording',
        default=False,
    )
    auto_record = fields.Boolean(
        string='Auto Record',
        default=False,
    )
    
    # Participants
    host_id = fields.Many2one(
        'res.users',
        string='Host',
        default=lambda self: self.env.user,
        required=True,
    )
    attendee_ids = fields.Many2many(
        'res.partner',
        'ringcentral_meeting_attendee_rel',
        'meeting_id',
        'partner_id',
        string='Attendees',
    )
    attendee_count = fields.Integer(
        compute='_compute_attendee_count',
        string='Attendees',
    )
    max_participants = fields.Integer(
        string='Max Participants',
        default=100,
    )
    
    # Calendar Integration
    calendar_event_id = fields.Many2one(
        'calendar.event',
        string='Calendar Event',
        ondelete='set null',
    )
    
    # Related Records
    res_model = fields.Char(string='Related Model')
    res_id = fields.Integer(string='Related ID')
    
    # Recording - stored as IDs only (related through call_id in ringcentral.recording)
    recording_count = fields.Integer(
        string='Recordings',
        compute='_compute_recording_count',
    )
    
    # Analytics
    participant_count = fields.Integer(
        string='Actual Participants',
        readonly=True,
    )
    
    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
    
    # Description
    description = fields.Html(string='Description')
    agenda = fields.Text(string='Agenda')

    @api.depends('scheduled_start', 'duration')
    def _compute_scheduled_end(self):
        for meeting in self:
            if meeting.scheduled_start and meeting.duration:
                meeting.scheduled_end = meeting.scheduled_start + timedelta(minutes=meeting.duration)

    @api.depends('attendee_ids')
    def _compute_attendee_count(self):
        for meeting in self:
            meeting.attendee_count = len(meeting.attendee_ids)

    def _compute_recording_count(self):
        """Compute count of recordings - will be 0 if ringcentral_recording not installed"""
        Recording = self.env.get('ringcentral.recording')
        for meeting in self:
            if Recording:
                meeting.recording_count = Recording.search_count([
                    ('res_model', '=', 'ringcentral.meeting'),
                    ('res_id', '=', meeting.id)
                ])
            else:
                meeting.recording_count = 0

    def action_schedule_meeting(self):
        """Create meeting in RingCentral"""
        self.ensure_one()
        
        rc_api = self.env['ringcentral.api'].sudo()
        
        try:
            result = rc_api.create_meeting({
                'name': self.name,
                'type': self.meeting_type,
                'startTime': self.scheduled_start.isoformat() if self.scheduled_start else None,
                'duration': self.duration,
                'password': self.password,
                'allowJoinBeforeHost': self.allow_join_before_host,
                'muteParticipantsOnEntry': self.mute_participants_on_entry,
                'enableWaitingRoom': self.enable_waiting_room,
                'enableRecording': self.enable_recording,
            })
            
            self.write({
                'ringcentral_meeting_id': result.get('id'),
                'bridge_id': result.get('bridges', [{}])[0].get('id'),
                'join_url': result.get('joinUrl'),
                'host_url': result.get('hostUrl'),
                'dial_in_number': result.get('dialInNumber'),
                'password': result.get('password') or self.password,
                'state': 'scheduled',
            })
            
            # Create/update calendar event
            self._sync_calendar_event()
            
            # Send invitations
            if self.attendee_ids:
                self._send_invitations()
            
            _logger.info(f'Meeting scheduled: {self.ringcentral_meeting_id}')
            
        except Exception as e:
            _logger.error(f'Failed to schedule meeting: {e}')
            raise UserError(_('Failed to schedule meeting: %s') % str(e))

    def action_start_meeting(self):
        """Start the meeting"""
        self.ensure_one()
        
        self.write({
            'state': 'started',
            'actual_start': fields.Datetime.now(),
        })
        
        # Open host URL
        if self.host_url:
            return {
                'type': 'ir.actions.act_url',
                'url': self.host_url,
                'target': 'new',
            }
        elif self.join_url:
            return {
                'type': 'ir.actions.act_url',
                'url': self.join_url,
                'target': 'new',
            }

    def action_join_meeting(self):
        """Join the meeting"""
        self.ensure_one()
        
        if self.join_url:
            return {
                'type': 'ir.actions.act_url',
                'url': self.join_url,
                'target': 'new',
            }
        
        raise UserError(_('Meeting link not available'))

    def action_end_meeting(self):
        """End the meeting"""
        self.ensure_one()
        
        rc_api = self.env['ringcentral.api'].sudo()
        
        try:
            if self.ringcentral_meeting_id:
                rc_api.end_meeting(self.ringcentral_meeting_id)
            
            self.write({
                'state': 'ended',
                'actual_end': fields.Datetime.now(),
            })
            
        except Exception as e:
            _logger.error(f'Failed to end meeting: {e}')
            # Still mark as ended locally
            self.write({
                'state': 'ended',
                'actual_end': fields.Datetime.now(),
            })

    def action_cancel_meeting(self):
        """Cancel the meeting"""
        self.ensure_one()
        
        rc_api = self.env['ringcentral.api'].sudo()
        
        try:
            if self.ringcentral_meeting_id:
                rc_api.delete_meeting(self.ringcentral_meeting_id)
            
            self.state = 'cancelled'
            
            # Cancel calendar event
            if self.calendar_event_id:
                self.calendar_event_id.active = False
            
        except Exception as e:
            _logger.error(f'Failed to cancel meeting: {e}')
            self.state = 'cancelled'

    def action_copy_join_link(self):
        """Copy join link to clipboard (triggers frontend action)"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Join link copied: %s') % self.join_url,
                'type': 'info',
                'sticky': False,
            }
        }

    def _sync_calendar_event(self):
        """Create or update calendar event"""
        self.ensure_one()
        
        CalendarEvent = self.env['calendar.event']
        
        # Build attendee list
        partner_ids = self.attendee_ids.ids
        if self.host_id.partner_id.id not in partner_ids:
            partner_ids.append(self.host_id.partner_id.id)
        
        event_vals = {
            'name': self.name,
            'start': self.scheduled_start,
            'stop': self.scheduled_end,
            'duration': self.duration / 60.0,  # hours
            'partner_ids': [(6, 0, partner_ids)],
            'user_id': self.host_id.id,
            'description': self._build_calendar_description(),
            'videocall_location': self.join_url,
            'videocall_source': 'ringcentral',
        }
        
        if self.calendar_event_id:
            self.calendar_event_id.write(event_vals)
        else:
            event = CalendarEvent.create(event_vals)
            self.calendar_event_id = event.id

    def _build_calendar_description(self):
        """Build meeting description for calendar"""
        lines = []
        
        if self.description:
            lines.append(self.description)
            lines.append('<br/><br/>')
        
        lines.append(f'<strong>Join Meeting:</strong> <a href="{self.join_url}">{self.join_url}</a>')
        
        if self.dial_in_number:
            lines.append(f'<br/><strong>Dial-in:</strong> {self.dial_in_number}')
        
        if self.password:
            lines.append(f'<br/><strong>Password:</strong> {self.password}')
        
        if self.agenda:
            lines.append(f'<br/><br/><strong>Agenda:</strong><br/>{self.agenda}')
        
        return ''.join(lines)

    def _send_invitations(self):
        """Send meeting invitations to attendees"""
        self.ensure_one()
        
        template = self.env.ref('ringcentral_meet.email_template_meeting_invitation', raise_if_not_found=False)
        
        if template:
            for partner in self.attendee_ids:
                template.send_mail(self.id, email_values={'recipient_ids': [(4, partner.id)]})
        else:
            # Fallback - send simple email
            self.message_post(
                body=_('Meeting scheduled: %s\nJoin: %s') % (self.name, self.join_url),
                partner_ids=self.attendee_ids.ids,
                message_type='notification',
                subtype_id=self.env.ref('mail.mt_comment').id,
            )

    def action_view_recordings(self):
        """View meeting recordings"""
        self.ensure_one()
        Recording = self.env.get('ringcentral.recording')
        if not Recording:
            raise UserError(_('Recording module not installed'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Recordings'),
            'res_model': 'ringcentral.recording',
            'view_mode': 'list,form',
            'domain': [('res_model', '=', 'ringcentral.meeting'), ('res_id', '=', self.id)],
        }

    @api.model
    def create_instant_meeting(self, name=None):
        """Quick create and start instant meeting"""
        meeting = self.create({
            'name': name or _('Instant Meeting'),
            'meeting_type': 'instant',
            'scheduled_start': fields.Datetime.now(),
        })
        meeting.action_schedule_meeting()
        return meeting.action_start_meeting()

    @api.model
    def process_meeting_webhook(self, data):
        """Process meeting webhook from RingCentral"""
        meeting_id = data.get('meetingId')
        event_type = data.get('eventType', '')
        
        if not meeting_id:
            return
        
        meeting = self.search([('ringcentral_meeting_id', '=', meeting_id)], limit=1)
        
        if not meeting:
            return
        
        if 'Started' in event_type:
            meeting.write({
                'state': 'started',
                'actual_start': fields.Datetime.now(),
            })
        elif 'Ended' in event_type:
            meeting.write({
                'state': 'ended',
                'actual_end': fields.Datetime.now(),
                'participant_count': data.get('participantCount', 0),
            })
