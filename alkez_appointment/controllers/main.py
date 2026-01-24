# Copyright 2024 Your Company
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import json
import pytz
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from dateutil.parser import isoparse

from odoo import http, fields, _
from odoo.http import request
from odoo.exceptions import AccessError, ValidationError


class AppointmentController(http.Controller):
    """Main controller for public appointment booking."""

    # =====================
    # PUBLIC BOOKING PAGES
    # =====================
    
    @http.route([
        '/appointment/<string:user_slug>',
        '/appointment/<string:user_slug>/',
    ], type='http', auth='public', website=True, sitemap=True)
    def appointment_user_page(self, user_slug, **kwargs):
        """User's public appointment page - lists all event types."""
        user = request.env['res.users'].sudo().search([
            ('appointment_slug', '=', user_slug)
        ], limit=1)
        
        if not user:
            return request.redirect('/404')
        
        # Get active appointment types for this user
        appointment_types = request.env['appointment.type'].sudo().search([
            ('user_ids', 'in', [user.id]),
            ('active', '=', True)
        ])
        
        values = {
            'user': user,
            'appointment_types': appointment_types,
            'is_embed': kwargs.get('embed_type'),
        }
        
        return request.render('alkez_appointment.appointment_user_page', values)

    @http.route([
        '/appointment/<string:user_slug>/<string:type_slug>',
        '/appointment/<string:user_slug>/<string:type_slug>/',
    ], type='http', auth='public', website=True, sitemap=True)
    def appointment_booking_page(self, user_slug, type_slug, **kwargs):
        """Appointment booking page with calendar."""
        user = request.env['res.users'].sudo().search([
            ('appointment_slug', '=', user_slug)
        ], limit=1)
        
        if not user:
            return request.redirect('/404')
        
        appointment_type = request.env['appointment.type'].sudo().search([
            ('slug', '=', type_slug),
            ('user_ids', 'in', [user.id]),
            ('active', '=', True)
        ], limit=1)
        
        if not appointment_type:
            return request.redirect('/404')
        
        # Get timezone from request or default
        timezone = kwargs.get('timezone', 'UTC')
        
        # Get selected month/year or current
        now = datetime.now(pytz.timezone(timezone))
        year = int(kwargs.get('year', now.year))
        month = int(kwargs.get('month', now.month))
        
        # Calculate date range for slots
        start_date = datetime(year, month, 1).date()
        end_date = (start_date + relativedelta(months=1)) - timedelta(days=1)
        
        # Format month display (e.g., "December 2025")
        month_display = datetime(year, month, 1).strftime('%B %Y')
        
        # Get available slots
        slots = appointment_type.get_available_slots(
            user_id=user.id,
            start_date=start_date,
            end_date=end_date,
            timezone=timezone
        )
        
        values = {
            'user': user,
            'appointment_type': appointment_type,
            'slots': slots,
            'slots_json': json.dumps(slots),
            'timezone': timezone,
            'current_month': month,
            'current_year': year,
            'month_display': month_display,
            'today': now.date(),
            'is_embed': kwargs.get('embed') or kwargs.get('embed_type'),
            'selected_date': kwargs.get('date'),
            'selected_time': kwargs.get('time'),
        }
        
        return request.render('alkez_appointment.appointment_booking_page', values)

    @http.route([
        '/appointment/<string:user_slug>/<string:type_slug>/book',
    ], type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def appointment_book(self, user_slug, type_slug, **post):
        """Process appointment booking form submission."""
        user = request.env['res.users'].sudo().search([
            ('appointment_slug', '=', user_slug)
        ], limit=1)
        
        appointment_type = request.env['appointment.type'].sudo().search([
            ('slug', '=', type_slug),
            ('user_ids', 'in', [user.id])
        ], limit=1)
        
        if not user or not appointment_type:
            return request.redirect('/404')
        
        # Parse datetime
        try:
            start_dt = isoparse(post.get('datetime'))
            if start_dt.tzinfo is None:
                tz = pytz.timezone(post.get('timezone', 'UTC'))
                start_dt = tz.localize(start_dt)
            # Convert to UTC for storage
            start_utc = start_dt.astimezone(pytz.UTC).replace(tzinfo=None)
        except Exception as e:
            return request.redirect(f'/appointment/{user_slug}/{type_slug}?error=invalid_time')
        
        # Determine the assigned user
        assigned_user_id = user.id
        if appointment_type.assign_method == 'chosen' and post.get('host_user_id'):
            # Invitee chose a specific host
            chosen_host_id = int(post.get('host_user_id'))
            # Validate that the chosen host is one of the allowed users
            if chosen_host_id in appointment_type.user_ids.ids:
                assigned_user_id = chosen_host_id
        
        # Create booking
        booking_vals = {
            'appointment_type_id': appointment_type.id,
            'user_id': assigned_user_id,
            'start': start_utc,
            'invitee_name': post.get('name'),
            'invitee_email': post.get('email'),
            'invitee_phone': post.get('phone'),
            'notes': post.get('notes'),
            'timezone': post.get('timezone', 'UTC'),
            'source': 'embed' if post.get('embed') else 'public',
        }
        
        # Add UTM tracking
        for utm in ['utm_source', 'utm_medium', 'utm_campaign']:
            if post.get(utm):
                booking_vals[utm] = post[utm]
        
        try:
            booking = request.env['appointment.booking'].sudo().create(booking_vals)
            
            # Process question answers
            for key, value in post.items():
                if key.startswith('question_'):
                    question_id = int(key.replace('question_', ''))
                    request.env['appointment.answer'].sudo().create({
                        'booking_id': booking.id,
                        'question_id': question_id,
                        'value_text': value,
                    })
            
            # Confirm the booking
            booking.action_confirm()
            
            return request.redirect(f'/appointment/confirmation/{booking.access_token}')
            
        except Exception as e:
            import logging
            import urllib.parse
            _logger = logging.getLogger(__name__)
            _logger.error(f"Appointment booking error: {e}", exc_info=True)
            # Sanitize error message for URL - remove newlines and limit length
            error_msg = str(e).replace('\n', ' ').replace('\r', '')[:200]
            error_msg = urllib.parse.quote(error_msg, safe='')
            return request.redirect(f'/appointment/{user_slug}/{type_slug}?error={error_msg}')

    @http.route([
        '/appointment/confirmation/<string:token>',
    ], type='http', auth='public', website=True)
    def appointment_confirmation(self, token, **kwargs):
        """Booking confirmation page."""
        booking = request.env['appointment.booking'].sudo().search([
            ('access_token', '=', token)
        ], limit=1)
        
        if not booking:
            return request.redirect('/404')
        
        # Format the appointment datetime for display
        appointment_datetime = ""
        if booking.start:
            try:
                tz = pytz.timezone(booking.timezone or 'UTC')
                local_start = booking.start.replace(tzinfo=pytz.UTC).astimezone(tz)
                appointment_datetime = local_start.strftime('%I:%M %p, %A, %B %d, %Y')
            except Exception:
                appointment_datetime = booking.start.strftime('%I:%M %p, %A, %B %d, %Y')
        
        values = {
            'booking': booking,
            'user': booking.user_id,
            'appointment_type': booking.appointment_type_id,
            'appointment_datetime': appointment_datetime,
            'timezone': booking.timezone or 'UTC',
            'is_embed': kwargs.get('embed_type'),
            'rescheduled': kwargs.get('rescheduled'),
        }
        
        return request.render('alkez_appointment.appointment_confirmation_page', values)

    # =====================
    # JSON API FOR CALENDAR
    # =====================
    
    @http.route('/appointment/slots', type='json', auth='public', website=True)
    def appointment_slots_json(self, appointment_type_id, user_id, start_date, end_date, timezone='UTC', **kwargs):
        """Get available slots as JSON for AJAX requests."""
        try:
            appointment_type = request.env['appointment.type'].sudo().browse(int(appointment_type_id))
            if not appointment_type.exists():
                return {'error': 'Invalid appointment type'}
            
            start = datetime.fromisoformat(start_date).date()
            end = datetime.fromisoformat(end_date).date()
            
            slots = appointment_type.get_available_slots(
                user_id=int(user_id),
                start_date=start,
                end_date=end,
                timezone=timezone
            )
            
            return {'slots': slots}
        except Exception as e:
            return {'error': str(e)}

    # =====================
    # DIRECT TYPE ACCESS
    # =====================
    
    @http.route([
        '/appointment/type/<int:type_id>',
    ], type='http', auth='public', website=True)
    def appointment_type_direct(self, type_id, **kwargs):
        """Direct access to appointment type."""
        appointment_type = request.env['appointment.type'].sudo().browse(type_id)
        
        if not appointment_type.exists() or not appointment_type.active:
            return request.render('website.404')
        
        # Check if users are assigned
        if not appointment_type.user_ids:
            return request.render('alkez_appointment.appointment_no_users', {
                'appointment_type': appointment_type,
            })
        
        # Redirect to first user's page
        user = appointment_type.user_ids[0]
        
        # Ensure user has appointment slug
        if not user.appointment_slug:
            return request.render('alkez_appointment.appointment_no_users', {
                'appointment_type': appointment_type,
                'error': 'User does not have an appointment slug configured.',
            })
        
        return request.redirect(f'/appointment/{user.appointment_slug}/{appointment_type.slug}')

    # =====================
    # INVITATION HANDLING
    # =====================
    
    @http.route([
        '/appointment/invite/<string:token>',
    ], type='http', auth='public', website=True)
    def appointment_invite(self, token, **kwargs):
        """Handle invitation link."""
        invite = request.env['appointment.invite'].sudo().search([
            ('access_token', '=', token),
            ('state', 'in', ['sent', 'draft'])
        ], limit=1)
        
        if not invite:
            return request.render('alkez_appointment.appointment_invite_expired')
        
        # Check expiration
        if invite.expires_at and invite.expires_at < fields.Datetime.now():
            invite.state = 'expired'
            return request.render('alkez_appointment.appointment_invite_expired')
        
        # Redirect to booking page with prefilled data
        user = invite.user_id
        apt_type = invite.appointment_type_id
        
        redirect_url = f'/appointment/{user.appointment_slug}/{apt_type.slug}'
        if invite.invitee_email:
            redirect_url += f'?email={invite.invitee_email}'
        if invite.invitee_name:
            redirect_url += f'&name={invite.invitee_name}'
        
        return request.redirect(redirect_url)

    # =====================
    # RESCHEDULE & CANCEL
    # =====================
    
    @http.route([
        '/appointment/booking/<int:booking_id>/reschedule',
    ], type='http', auth='public', website=True)
    def appointment_reschedule(self, booking_id, token=None, **kwargs):
        """Reschedule booking page."""
        booking = request.env['appointment.booking'].sudo().browse(booking_id)
        
        if not booking.exists() or booking.access_token != token:
            return request.redirect('/404')
        
        if not booking.can_reschedule:
            return request.render('alkez_appointment.appointment_cannot_reschedule', {'booking': booking})
        
        user = booking.user_id
        apt_type = booking.appointment_type_id
        
        # Get timezone
        timezone = kwargs.get('timezone', booking.timezone or 'UTC')
        now = datetime.now(pytz.timezone(timezone))
        year = int(kwargs.get('year', now.year))
        month = int(kwargs.get('month', now.month))
        
        start_date = datetime(year, month, 1).date()
        end_date = (start_date + relativedelta(months=1)) - timedelta(days=1)
        
        slots = apt_type.get_available_slots(
            user_id=user.id,
            start_date=start_date,
            end_date=end_date,
            timezone=timezone
        )
        
        values = {
            'booking': booking,
            'user': user,
            'appointment_type': apt_type,
            'slots': slots,
            'slots_json': json.dumps(slots),
            'timezone': timezone,
            'current_month': month,
            'current_year': year,
            'is_reschedule': True,
        }
        
        return request.render('alkez_appointment.appointment_reschedule_page', values)

    @http.route([
        '/appointment/booking/<int:booking_id>/reschedule/confirm',
    ], type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def appointment_reschedule_confirm(self, booking_id, token=None, **post):
        """Process reschedule."""
        booking = request.env['appointment.booking'].sudo().browse(booking_id)
        
        if not booking.exists() or booking.access_token != token:
            return request.redirect('/404')
        
        try:
            start_dt = isoparse(post.get('datetime'))
            if start_dt.tzinfo is None:
                tz = pytz.timezone(post.get('timezone', 'UTC'))
                start_dt = tz.localize(start_dt)
            start_utc = start_dt.astimezone(pytz.UTC).replace(tzinfo=None)
            
            booking.write({
                'start': start_utc,
                'timezone': post.get('timezone', 'UTC'),
            })
            
            # Send reschedule notification (fixed template reference)
            template = request.env.ref('appointment.mail_template_booking_reschedule', raise_if_not_found=False)
            if template:
                template.sudo().send_mail(booking.id, force_send=True)
            
            return request.redirect(f'/appointment/confirmation/{booking.access_token}?rescheduled=1')
            
        except Exception as e:
            return request.redirect(f'/appointment/booking/{booking_id}/reschedule?token={token}&error={str(e)}')

    @http.route([
        '/appointment/booking/<int:booking_id>/cancel',
    ], type='http', auth='public', website=True)
    def appointment_cancel_page(self, booking_id, token=None, **kwargs):
        """Cancel confirmation page."""
        booking = request.env['appointment.booking'].sudo().browse(booking_id)
        
        if not booking.exists() or booking.access_token != token:
            return request.redirect('/404')
        
        if not booking.can_cancel:
            return request.render('alkez_appointment.appointment_cannot_cancel', {'booking': booking})
        
        values = {
            'booking': booking,
        }
        
        return request.render('alkez_appointment.appointment_cancel_page', values)

    @http.route([
        '/appointment/booking/<int:booking_id>/cancel/confirm',
    ], type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def appointment_cancel_confirm(self, booking_id, token=None, **post):
        """Process cancellation."""
        booking = request.env['appointment.booking'].sudo().browse(booking_id)
        
        if not booking.exists() or booking.access_token != token:
            return request.redirect('/404')
        
        booking.action_cancel()
        
        return request.render('alkez_appointment.appointment_cancelled', {'booking': booking})

    # =====================
    # JSON API ENDPOINTS
    # =====================
    
    @http.route([
        '/appointment/api/slots/<int:type_id>',
    ], type='json', auth='public', methods=['POST'])
    def api_get_slots(self, type_id, user_id=None, month=None, year=None, timezone='UTC', **kwargs):
        """API endpoint to get available slots."""
        appointment_type = request.env['appointment.type'].sudo().browse(type_id)
        
        if not appointment_type.exists():
            return {'error': 'Appointment type not found'}
        
        now = datetime.now(pytz.timezone(timezone))
        year = year or now.year
        month = month or now.month
        
        start_date = datetime(year, month, 1).date()
        end_date = (start_date + relativedelta(months=1)) - timedelta(days=1)
        
        slots = appointment_type.get_available_slots(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            timezone=timezone
        )
        
        return {
            'slots': slots,
            'month': month,
            'year': year,
            'timezone': timezone,
        }

    @http.route([
        '/appointment/api/book',
    ], type='json', auth='public', methods=['POST'])
    def api_book_appointment(self, type_id, datetime_str, name, email, 
                             phone=None, timezone='UTC', answers=None, **kwargs):
        """API endpoint to create booking."""
        appointment_type = request.env['appointment.type'].sudo().browse(type_id)
        
        if not appointment_type.exists():
            return {'error': 'Appointment type not found'}
        
        try:
            start_dt = isoparse(datetime_str)
            if start_dt.tzinfo is None:
                tz = pytz.timezone(timezone)
                start_dt = tz.localize(start_dt)
            start_utc = start_dt.astimezone(pytz.UTC).replace(tzinfo=None)
        except Exception:
            return {'error': 'Invalid datetime format'}
        
        # Assign user
        user = None
        if appointment_type.user_ids:
            user = appointment_type.user_ids[0]
        
        booking_vals = {
            'appointment_type_id': type_id,
            'user_id': user.id if user else False,
            'start': start_utc,
            'invitee_name': name,
            'invitee_email': email,
            'invitee_phone': phone,
            'timezone': timezone,
            'source': 'embed',
        }
        
        try:
            booking = request.env['appointment.booking'].sudo().create(booking_vals)
            
            # Process answers
            if answers:
                for question_id, value in answers.items():
                    request.env['appointment.answer'].sudo().create({
                        'booking_id': booking.id,
                        'question_id': int(question_id),
                        'value_text': value,
                    })
            
            booking.action_confirm()
            
            return {
                'success': True,
                'booking_id': booking.id,
                'access_token': booking.access_token,
                'confirmation_url': f'/appointment/confirmation/{booking.access_token}',
            }
            
        except Exception as e:
            return {'error': str(e)}

    @http.route([
        '/appointment/api/timezones',
    ], type='json', auth='public', methods=['POST'])
    def api_get_timezones(self, **kwargs):
        """Get list of common timezones."""
        import pytz
        
        common_timezones = [
            'America/New_York',
            'America/Chicago',
            'America/Denver',
            'America/Los_Angeles',
            'America/Toronto',
            'Europe/London',
            'Europe/Paris',
            'Europe/Berlin',
            'Asia/Dubai',
            'Asia/Singapore',
            'Asia/Tokyo',
            'Australia/Sydney',
            'Pacific/Auckland',
        ]
        
        result = []
        for tz_name in pytz.common_timezones:
            try:
                tz = pytz.timezone(tz_name)
                now = datetime.now(tz)
                offset = now.strftime('%z')
                offset_formatted = f"UTC{offset[:3]}:{offset[3:]}"
                result.append({
                    'name': tz_name,
                    'offset': offset_formatted,
                    'is_common': tz_name in common_timezones,
                })
            except Exception:
                continue
        
        # Sort by offset and name
        result.sort(key=lambda x: (not x['is_common'], x['offset'], x['name']))
        
        return result

    # =====================
    # CALENDAR OAUTH CALLBACKS
    # =====================
    
    @http.route([
        '/appointment/calendar/google/callback',
    ], type='http', auth='user', website=True)
    def google_oauth_callback(self, code=None, state=None, error=None, **kwargs):
        """Handle Google Calendar OAuth callback."""
        if error:
            return request.render('alkez_appointment.oauth_error', {
                'error': error,
                'provider': 'Google Calendar'
            })
        
        if not code or not state:
            return request.redirect('/my/appointments')
        
        try:
            sync_id = int(state)
            sync = request.env['appointment.calendar.sync'].browse(sync_id)
            
            if not sync.exists() or sync.user_id != request.env.user:
                raise ValueError("Invalid sync configuration")
            
            # Exchange code for tokens
            ICP = request.env['ir.config_parameter'].sudo()
            client_id = ICP.get_param('appointment.google_client_id')
            client_secret = ICP.get_param('appointment.google_client_secret')
            base_url = ICP.get_param('web.base.url')
            redirect_uri = f"{base_url}/appointment/calendar/google/callback"
            
            import urllib.request
            import urllib.parse
            
            data = urllib.parse.urlencode({
                'code': code,
                'client_id': client_id,
                'client_secret': client_secret,
                'redirect_uri': redirect_uri,
                'grant_type': 'authorization_code',
            }).encode()
            
            req = urllib.request.Request(
                'https://oauth2.googleapis.com/token',
                data=data,
                method='POST'
            )
            
            response = urllib.request.urlopen(req)
            token_data = json.loads(response.read().decode())
            
            sync.write({
                'state': 'connected',
                'access_token': token_data['access_token'],
                'refresh_token': token_data.get('refresh_token'),
                'token_expires': fields.Datetime.now() + timedelta(seconds=token_data['expires_in']),
            })
            
            return request.redirect('/my/appointments?calendar_connected=google')
            
        except Exception as e:
            return request.render('alkez_appointment.oauth_error', {
                'error': str(e),
                'provider': 'Google Calendar'
            })

    @http.route([
        '/appointment/calendar/outlook/callback',
    ], type='http', auth='user', website=True)
    def outlook_oauth_callback(self, code=None, state=None, error=None, **kwargs):
        """Handle Microsoft Outlook OAuth callback."""
        if error:
            return request.render('alkez_appointment.oauth_error', {
                'error': error,
                'provider': 'Microsoft Outlook'
            })
        
        if not code or not state:
            return request.redirect('/my/appointments')
        
        try:
            sync_id = int(state)
            sync = request.env['appointment.calendar.sync'].browse(sync_id)
            
            if not sync.exists() or sync.user_id != request.env.user:
                raise ValueError("Invalid sync configuration")
            
            # Exchange code for tokens
            ICP = request.env['ir.config_parameter'].sudo()
            client_id = ICP.get_param('appointment.outlook_client_id')
            client_secret = ICP.get_param('appointment.outlook_client_secret')
            base_url = ICP.get_param('web.base.url')
            redirect_uri = f"{base_url}/appointment/calendar/outlook/callback"
            
            import urllib.request
            import urllib.parse
            
            data = urllib.parse.urlencode({
                'code': code,
                'client_id': client_id,
                'client_secret': client_secret,
                'redirect_uri': redirect_uri,
                'grant_type': 'authorization_code',
                'scope': 'Calendars.ReadWrite offline_access',
            }).encode()
            
            req = urllib.request.Request(
                'https://login.microsoftonline.com/common/oauth2/v2.0/token',
                data=data,
                method='POST',
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            response = urllib.request.urlopen(req)
            token_data = json.loads(response.read().decode())
            
            sync.write({
                'state': 'connected',
                'access_token': token_data['access_token'],
                'refresh_token': token_data.get('refresh_token'),
                'token_expires': fields.Datetime.now() + timedelta(seconds=token_data['expires_in']),
            })
            
            return request.redirect('/my/appointments?calendar_connected=outlook')
            
        except Exception as e:
            return request.render('alkez_appointment.oauth_error', {
                'error': str(e),
                'provider': 'Microsoft Outlook'
            })

