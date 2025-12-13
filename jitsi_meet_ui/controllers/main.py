# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class JitsiController(http.Controller):
    
    @http.route('/o-meet/join/<string:room>', type='http', auth='public', website=True)
    def join_meeting(self, room, **kw):
        """Public meeting join page - anyone with link can join"""
        # Find meeting by room code
        meeting = request.env['jitsi.meeting'].sudo().search([('room_name', '=', room)], limit=1)
        server = request.env['ir.config_parameter'].sudo().get_param('jitsi.server.url') or 'https://meet.jit.si'
        
        # Get current user info (if authenticated)
        user = request.env.user
        user_name = user.name if user and user.id != request.env.ref('base.public_user').id else 'Guest'
        user_email = user.email if user and user.id != request.env.ref('base.public_user').id else ''
        
        # Check if user is meeting owner (becomes moderator)
        is_moderator = meeting and user.id == meeting.owner_id.id
        
        # Generate JWT token if configured (for all users, not just moderators)
        jwt_token = None
        if meeting:
            jwt_token = meeting.generate_jwt_token(user_name, user_email, is_moderator=is_moderator)
        
        meeting_data = {
            'jitsi_server': server,
            'room': room,
            'meeting_title': meeting.name if meeting else f'Meeting {room}',
            'meeting_exists': bool(meeting),
            'user_name': user_name,
            'user_email': user_email,
            'jwt_token': jwt_token,
            'is_moderator': is_moderator,
        }
        
        return request.render('jitsi_meet_ui.jitsi_room_template', meeting_data)
    
    @http.route('/o-meet/dashboard', type='http', auth='user', website=True)
    def dashboard(self, **kw):
        """Main O-Meet dashboard - Google Meet style"""
        meetings = request.env['jitsi.meeting'].search([
            ('owner_id', '=', request.env.user.id),
            ('state', 'in', ['ready', 'started'])
        ], order='start_datetime desc', limit=10)
        
        return request.render('jitsi_meet_ui.omeet_dashboard', {
            'meetings': meetings,
        })
    
    @http.route('/o-meet/instant', type='json', auth='user')
    def create_instant(self, **kw):
        """Create instant meeting via JSON RPC"""
        meeting = request.env['jitsi.meeting'].create_instant_meeting()
        return meeting
