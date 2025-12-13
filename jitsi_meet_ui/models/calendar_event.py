# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    videocall_source = fields.Selection(
        selection_add=[('jitsi', 'O-Meet (Jitsi)')],
        ondelete={'jitsi': 'cascade'}
    )
    jitsi_meeting_id = fields.Many2one(
        'jitsi.meeting',
        string='Jitsi Meeting',
        ondelete='set null',
        help='Link to O-Meet Jitsi meeting'
    )

    @api.depends('videocall_source', 'jitsi_meeting_id', 'access_token')
    def _compute_videocall_location(self):
        """Override to add Jitsi meeting URL"""
        jitsi_events = self.filtered(lambda e: e.videocall_source == 'jitsi' and e.jitsi_meeting_id)
        for event in jitsi_events:
            event.videocall_location = event.jitsi_meeting_id.meeting_url
        
        # Call super for other videocall sources
        super(CalendarEvent, self - jitsi_events)._compute_videocall_location()

    def action_create_jitsi_meeting(self):
        """Create Jitsi meeting for calendar event"""
        self.ensure_one()
        
        if not self.jitsi_meeting_id:
            # Create instant or scheduled meeting based on event start
            JitsiMeeting = self.env['jitsi.meeting']
            meeting_vals = {
                'name': self.name or 'Calendar Meeting',
                'start_datetime': self.start,
                'duration': (self.stop - self.start).total_seconds() / 3600.0,  # Convert to hours
                'owner_id': self.user_id.id or self.env.user.id,
                'meeting_type': 'scheduled',
                'state': 'ready',
            }
            
            # Add attendees from calendar event
            if self.partner_ids:
                users = self.env['res.users'].search([('partner_id', 'in', self.partner_ids.ids)])
                if users:
                    meeting_vals['attendee_ids'] = [(6, 0, users.ids)]
            
            meeting = JitsiMeeting.create(meeting_vals)
            self.jitsi_meeting_id = meeting.id
            self.videocall_source = 'jitsi'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('O-Meet Created'),
                'message': _('Jitsi meeting link: %s') % self.jitsi_meeting_id.meeting_url,
                'type': 'success',
                'sticky': True,
            }
        }

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-create Jitsi meeting if videocall_source is jitsi"""
        events = super().create(vals_list)
        for event in events:
            if event.videocall_source == 'jitsi' and not event.jitsi_meeting_id:
                event.action_create_jitsi_meeting()
        return events

    def write(self, vals):
        """Update Jitsi meeting when calendar event is updated"""
        res = super().write(vals)
        
        # If videocall source changed to jitsi, create meeting
        if vals.get('videocall_source') == 'jitsi':
            for event in self:
                if not event.jitsi_meeting_id:
                    event.action_create_jitsi_meeting()
        
        # Update linked Jitsi meeting details
        for event in self:
            if event.jitsi_meeting_id and any(k in vals for k in ['name', 'start', 'stop']):
                meeting_vals = {}
                if 'name' in vals:
                    meeting_vals['name'] = event.name
                if 'start' in vals:
                    meeting_vals['start_datetime'] = event.start
                if 'stop' in vals and event.start:
                    meeting_vals['duration'] = (event.stop - event.start).total_seconds() / 3600.0
                
                if meeting_vals:
                    event.jitsi_meeting_id.write(meeting_vals)
        
        return res
