# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    # RingCentral Meeting Integration
    ringcentral_meeting_id = fields.Many2one(
        'ringcentral.meeting',
        string='RingCentral Meeting',
        ondelete='set null',
    )
    videocall_source = fields.Selection(
        selection_add=[('ringcentral', 'RingCentral')],
        ondelete={'ringcentral': 'set null'},
    )

    def action_create_ringcentral_meeting(self):
        """Create RingCentral meeting for this calendar event"""
        self.ensure_one()
        
        Meeting = self.env['ringcentral.meeting']
        
        # Check if meeting already exists
        if self.ringcentral_meeting_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'ringcentral.meeting',
                'res_id': self.ringcentral_meeting_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        
        # Calculate duration in minutes
        duration = (self.stop - self.start).total_seconds() / 60
        
        meeting_vals = {
            'name': self.name,
            'scheduled_start': self.start,
            'duration': int(duration),
            'host_id': self.user_id.id if self.user_id else self.env.user.id,
            'attendee_ids': [(6, 0, self.partner_ids.ids)],
            'calendar_event_id': self.id,
            'description': self.description,
        }
        
        meeting = Meeting.create(meeting_vals)
        self.ringcentral_meeting_id = meeting.id
        
        # Schedule the meeting in RingCentral
        meeting.action_schedule_meeting()
        
        # Update calendar event with meeting link
        self.videocall_location = meeting.join_url
        self.videocall_source = 'ringcentral'
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ringcentral.meeting',
            'res_id': meeting.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_join_ringcentral_meeting(self):
        """Join the RingCentral meeting"""
        self.ensure_one()
        
        if self.ringcentral_meeting_id:
            return self.ringcentral_meeting_id.action_join_meeting()
        elif self.videocall_location:
            return {
                'type': 'ir.actions.act_url',
                'url': self.videocall_location,
                'target': 'new',
            }
