# -*- coding: utf-8 -*-
import uuid
import jwt
import time
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class JitsiMeeting(models.Model):
    _name = 'jitsi.meeting'
    _description = 'Jitsi Meeting'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_datetime desc'

    name = fields.Char(string='Title', required=True, index=True, default='New Meeting')
    room_name = fields.Char(string='Room Code', required=True, default=lambda self: 'meet-' + uuid.uuid4().hex[:10], index=True)
    meeting_type = fields.Selection([
        ('instant', 'Instant Meeting'),
        ('scheduled', 'Scheduled Meeting')
    ], string='Type', default='instant', required=True)
    start_datetime = fields.Datetime(string='Scheduled For', default=fields.Datetime.now)
    duration = fields.Integer(string='Duration (minutes)', default=60)
    owner_id = fields.Many2one('res.users', string='Organizer', default=lambda self: self.env.user, required=True)
    attendee_ids = fields.Many2many('res.users', string='Attendees')
    meeting_url = fields.Char(string='Meeting Link', compute='_compute_meeting_url', store=False)
    join_url = fields.Char(string='Join URL', compute='_compute_meeting_url', store=False)
    active = fields.Boolean(default=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('ready', 'Ready'),
        ('started', 'Started'),
        ('ended', 'Ended')
    ], default='ready', string='Status')

    @api.depends('room_name')
    def _compute_meeting_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') or 'http://localhost:8069'
        for rec in self:
            rec.meeting_url = f"{base_url}/o-meet/join/{rec.room_name}"
            rec.join_url = rec.meeting_url

    @api.model
    def create_instant_meeting(self):
        """Create and immediately return a ready-to-join instant meeting"""
        meeting = self.create({
            'name': f'Instant Meeting - {fields.Datetime.now().strftime("%b %d, %H:%M")}',
            'meeting_type': 'instant',
            'state': 'ready',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': meeting.meeting_url,
            'target': 'new',
        }

    @api.model
    def create_scheduled_meeting(self, vals):
        """Create a scheduled meeting and return meeting details"""
        vals['meeting_type'] = 'scheduled'
        vals['state'] = 'ready'
        meeting = self.create(vals)
        return meeting

    def action_join(self):
        """Open meeting in new tab"""
        self.ensure_one()
        if self.state == 'ready':
            self.state = 'started'
        return {
            'type': 'ir.actions.act_url',
            'url': self.meeting_url,
            'target': 'new',
        }

    def action_copy_link(self):
        """Return meeting link for clipboard copy"""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Meeting Link'),
                'message': self.meeting_url,
                'sticky': False,
                'type': 'info',
            }
        }

    def generate_jwt_token(self, user_name, user_email, is_moderator=True):
        """Generate JWT token for Jitsi authentication (if configured)"""
        ICP = self.env['ir.config_parameter'].sudo()
        app_id = ICP.get_param('jitsi.jwt.app_id', '')
        app_secret = ICP.get_param('jitsi.jwt.app_secret', '')
        
        if not app_id or not app_secret:
            # No JWT configured, return None (will use public meet.jit.si)
            return None
        
        now = int(time.time())
        payload = {
            'iss': app_id,
            'aud': app_id,
            'exp': now + 7200,  # Token valid for 2 hours
            'nbf': now - 10,
            'sub': ICP.get_param('jitsi.server.domain', 'meet.jit.si'),
            'room': self.room_name,
            'context': {
                'user': {
                    'name': user_name,
                    'email': user_email,
                    'moderator': 'true' if is_moderator else 'false',
                },
            },
        }
        
        token = jwt.encode(payload, app_secret, algorithm='HS256')
        return token if isinstance(token, str) else token.decode('utf-8')

    @api.constrains('room_name')
    def _check_room_name(self):
        for rec in self:
            if not rec.room_name:
                raise ValidationError(_('Room name cannot be empty'))
