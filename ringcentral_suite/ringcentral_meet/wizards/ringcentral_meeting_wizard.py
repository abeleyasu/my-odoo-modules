# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import timedelta


class RingCentralMeetingWizard(models.TransientModel):
    _name = 'ringcentral.meeting.wizard'
    _description = 'Create RingCentral Meeting'

    name = fields.Char(
        string='Meeting Name',
        required=True,
        default=lambda self: _('Meeting on %s') % fields.Date.today(),
    )
    meeting_type = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('instant', 'Instant'),
    ], string='Type', default='scheduled', required=True)
    
    scheduled_start = fields.Datetime(
        string='Start Time',
        default=lambda self: fields.Datetime.now() + timedelta(hours=1),
    )
    duration = fields.Integer(
        string='Duration (minutes)',
        default=60,
    )
    
    # Settings
    password = fields.Char(string='Meeting Password')
    enable_waiting_room = fields.Boolean(
        string='Enable Waiting Room',
        default=True,
    )
    mute_participants_on_entry = fields.Boolean(
        string='Mute on Entry',
        default=True,
    )
    enable_recording = fields.Boolean(
        string='Enable Recording',
        default=False,
    )
    
    # Attendees
    attendee_ids = fields.Many2many(
        'res.partner',
        string='Attendees',
    )
    
    # Context
    res_model = fields.Char(string='Related Model')
    res_id = fields.Integer(string='Related ID')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        
        # Get context for related record
        if self.env.context.get('active_model'):
            res['res_model'] = self.env.context['active_model']
            res['res_id'] = self.env.context.get('active_id')
            
            # Try to get attendees from partner
            if res['res_model'] == 'res.partner':
                res['attendee_ids'] = [(6, 0, [res['res_id']])]
            elif res['res_model'] in ('crm.lead', 'helpdesk.ticket', 'project.task'):
                record = self.env[res['res_model']].browse(res['res_id'])
                if hasattr(record, 'partner_id') and record.partner_id:
                    res['attendee_ids'] = [(6, 0, [record.partner_id.id])]
        
        return res

    def action_create_meeting(self):
        """Create the meeting"""
        self.ensure_one()
        
        Meeting = self.env['ringcentral.meeting']
        
        meeting_vals = {
            'name': self.name,
            'meeting_type': self.meeting_type,
            'scheduled_start': self.scheduled_start,
            'duration': self.duration,
            'password': self.password,
            'enable_waiting_room': self.enable_waiting_room,
            'mute_participants_on_entry': self.mute_participants_on_entry,
            'enable_recording': self.enable_recording,
            'attendee_ids': [(6, 0, self.attendee_ids.ids)],
            'res_model': self.res_model,
            'res_id': self.res_id,
        }
        
        meeting = Meeting.create(meeting_vals)
        
        # Schedule in RingCentral
        meeting.action_schedule_meeting()
        
        if self.meeting_type == 'instant':
            return meeting.action_start_meeting()
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ringcentral.meeting',
            'res_id': meeting.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_create_instant(self):
        """Create and start instant meeting"""
        self.meeting_type = 'instant'
        self.scheduled_start = fields.Datetime.now()
        return self.action_create_meeting()
