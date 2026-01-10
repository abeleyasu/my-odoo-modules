# Copyright 2024 Your Company
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging
import uuid
import pytz
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class AppointmentBooking(models.Model):
    _name = "appointment.booking"
    _description = "Appointment Booking"
    _inherit = ["mail.thread", "mail.activity.mixin", "portal.mixin"]
    _order = "start desc"

    # =====================
    # IDENTIFICATION
    # =====================
    name = fields.Char(
        string="Reference",
        compute="_compute_name",
        store=True
    )
    access_token = fields.Char(
        string="Access Token",
        default=lambda self: str(uuid.uuid4()),
        copy=False
    )
    
    # =====================
    # APPOINTMENT TYPE
    # =====================
    appointment_type_id = fields.Many2one(
        'appointment.type',
        string="Event Type",
        required=True,
        ondelete='cascade',
        tracking=True
    )
    
    # =====================
    # SCHEDULING
    # =====================
    start = fields.Datetime(
        string="Start",
        tracking=True,
        index=True
    )
    stop = fields.Datetime(
        string="End",
        compute="_compute_stop",
        store=True
    )
    duration = fields.Float(
        string="Duration",
        compute="_compute_duration",
        store=True,
        readonly=False
    )
    
    timezone = fields.Char(
        string="Timezone",
        default='UTC'
    )
    
    # =====================
    # STATE
    # =====================
    state = fields.Selection([
        ('pending', 'Pending'),
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ], string="Status", default='pending', tracking=True, index=True)
    
    active = fields.Boolean(default=True)
    
    # =====================
    # INVITEE
    # =====================
    partner_id = fields.Many2one(
        'res.partner',
        string="Invitee",
        tracking=True
    )
    invitee_name = fields.Char(string="Name", required=True)
    invitee_email = fields.Char(string="Email", required=True)
    invitee_phone = fields.Char(string="Phone")
    
    # Aliases for backwards compatibility
    email = fields.Char(related='invitee_email', string="Email (Alias)", readonly=False)
    phone = fields.Char(related='invitee_phone', string="Phone (Alias)", readonly=False)
    
    # =====================
    # HOST
    # =====================
    user_id = fields.Many2one(
        'res.users',
        string="Host",
        tracking=True,
        index=True
    )
    
    # =====================
    # LOCATION
    # =====================
    location_type = fields.Selection(
        related='appointment_type_id.location_type',
        store=True
    )
    location = fields.Char(string="Location")
    video_link = fields.Char(string="Video Conference Link")
    
    # =====================
    # CALENDAR INTEGRATION
    # =====================
    calendar_event_id = fields.Many2one(
        'calendar.event',
        string="Calendar Event",
        ondelete='set null',
        copy=False
    )
    
    # =====================
    # QUESTIONS & ANSWERS
    # =====================
    answer_ids = fields.One2many(
        'appointment.answer',
        'booking_id',
        string="Answers"
    )
    
    notes = fields.Text(string="Additional Notes")
    internal_notes = fields.Text(string="Internal Notes")
    
    # =====================
    # EMAIL TRACKING (Enterprise Feature)
    # =====================
    reminder_sent = fields.Boolean(string="Reminder Sent", default=False, copy=False)
    reminder_sent_date = fields.Datetime(string="Reminder Sent At", copy=False)
    followup_sent = fields.Boolean(string="Follow-up Sent", default=False, copy=False)
    followup_sent_date = fields.Datetime(string="Follow-up Sent At", copy=False)
    host_notified = fields.Boolean(string="Host Notified", default=False, copy=False)
    
    # =====================
    # CANCELLATION
    # =====================
    cancel_reason = fields.Text(string="Cancellation Reason")
    cancelled_by = fields.Selection([
        ('invitee', 'Invitee'),
        ('host', 'Host'),
        ('system', 'System'),
    ], string="Cancelled By")
    cancel_date = fields.Datetime(string="Cancellation Date")
    
    # =====================
    # GROUP BOOKING
    # =====================
    is_group_booking = fields.Boolean(
        string="Group Booking",
        compute="_compute_is_group_booking",
        store=True
    )
    attendee_ids = fields.One2many(
        'appointment.booking.attendee',
        'booking_id',
        string="Additional Attendees"
    )
    attendee_count = fields.Integer(
        string="Attendee Count",
        compute="_compute_attendee_count",
        store=True
    )
    remaining_seats = fields.Integer(
        string="Remaining Seats",
        compute="_compute_remaining_seats"
    )
    
    # =====================
    # RECURRING APPOINTMENTS
    # =====================
    is_recurring = fields.Boolean(string="Recurring Appointment", default=False)
    recurring_pattern = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('biweekly', 'Every 2 Weeks'),
        ('monthly', 'Monthly'),
    ], string="Recurring Pattern")
    recurring_count = fields.Integer(
        string="Number of Occurrences",
        default=1
    )
    recurring_parent_id = fields.Many2one(
        'appointment.booking',
        string="Parent Booking",
        ondelete='cascade'
    )
    recurring_child_ids = fields.One2many(
        'appointment.booking',
        'recurring_parent_id',
        string="Recurring Instances"
    )
    recurring_index = fields.Integer(
        string="Occurrence #",
        default=0
    )
    
    # =====================
    # SOURCE TRACKING
    # =====================
    source = fields.Selection([
        ('public', 'Public Page'),
        ('embed', 'Embedded Widget'),
        ('invite', 'Direct Invite'),
        ('backend', 'Backend'),
    ], string="Source", default='public')
    
    utm_source = fields.Char(string="UTM Source")
    utm_medium = fields.Char(string="UTM Medium")
    utm_campaign = fields.Char(string="UTM Campaign")
    
    # =====================
    # COMPUTED FIELDS
    # =====================
    is_past = fields.Boolean(compute="_compute_is_past")
    is_upcoming = fields.Boolean(compute="_compute_is_upcoming")
    can_cancel = fields.Boolean(compute="_compute_can_cancel")
    can_reschedule = fields.Boolean(compute="_compute_can_reschedule")
    
    reschedule_url = fields.Char(compute="_compute_urls")
    cancel_url = fields.Char(compute="_compute_urls")
    
    @api.depends('invitee_name', 'appointment_type_id', 'start')
    def _compute_name(self):
        for record in self:
            parts = []
            if record.invitee_name:
                parts.append(record.invitee_name)
            if record.appointment_type_id:
                parts.append(record.appointment_type_id.name)
            if record.start:
                parts.append(record.start.strftime('%Y-%m-%d %H:%M'))
            record.name = ' - '.join(parts) if parts else _('New Booking')

    @api.depends('start', 'duration')
    def _compute_stop(self):
        for record in self:
            if record.start and record.duration:
                record.stop = record.start + timedelta(hours=record.duration)
            else:
                record.stop = False

    @api.depends('appointment_type_id.duration')
    def _compute_duration(self):
        for record in self:
            if not record.duration and record.appointment_type_id:
                record.duration = record.appointment_type_id.duration

    def _compute_is_past(self):
        now = fields.Datetime.now()
        for record in self:
            record.is_past = record.start and record.start < now

    def _compute_is_upcoming(self):
        now = fields.Datetime.now()
        for record in self:
            record.is_upcoming = record.start and record.start > now and record.state == 'confirmed'

    def _compute_can_cancel(self):
        now = fields.Datetime.now()
        for record in self:
            record.can_cancel = (
                record.state in ('scheduled', 'confirmed') and 
                record.start and 
                record.start > now
            )

    def _compute_can_reschedule(self):
        now = fields.Datetime.now()
        for record in self:
            min_notice = timedelta(hours=record.appointment_type_id.min_schedule_notice or 0)
            record.can_reschedule = (
                record.state in ('scheduled', 'confirmed') and 
                record.start and 
                record.start > now + min_notice
            )

    def _compute_urls(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for record in self:
            record.reschedule_url = f"{base_url}/appointment/booking/{record.id}/reschedule?token={record.access_token}"
            record.cancel_url = f"{base_url}/appointment/booking/{record.id}/cancel?token={record.access_token}"

    def _compute_access_url(self):
        for record in self:
            record.access_url = f"/my/appointments/{record.id}"

    @api.depends('appointment_type_id.allow_group_booking')
    def _compute_is_group_booking(self):
        for record in self:
            record.is_group_booking = record.appointment_type_id.allow_group_booking

    @api.depends('attendee_ids')
    def _compute_attendee_count(self):
        for record in self:
            # Count primary invitee + additional attendees
            record.attendee_count = 1 + len(record.attendee_ids)

    def _compute_remaining_seats(self):
        for record in self:
            if record.appointment_type_id.allow_group_booking:
                max_seats = record.appointment_type_id.max_attendees
                # Count all bookings at this slot
                slot_bookings = self.search([
                    ('appointment_type_id', '=', record.appointment_type_id.id),
                    ('start', '=', record.start),
                    ('state', 'in', ['scheduled', 'confirmed']),
                ])
                total_attendees = sum(b.attendee_count for b in slot_bookings)
                record.remaining_seats = max_seats - total_attendees
            else:
                record.remaining_seats = 0

    # =====================
    # CRUD OVERRIDES
    # =====================
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Create or find partner
            if vals.get('invitee_email') and not vals.get('partner_id'):
                partner = self.env['res.partner'].search([
                    ('email', '=ilike', vals['invitee_email'])
                ], limit=1)
                if not partner:
                    partner = self.env['res.partner'].create({
                        'name': vals.get('invitee_name', vals['invitee_email']),
                        'email': vals['invitee_email'],
                        'phone': vals.get('invitee_phone'),
                    })
                vals['partner_id'] = partner.id
        
        records = super().create(vals_list)
        
        for record in records:
            # Auto-assign user if round-robin or least-busy
            if not record.user_id and record.appointment_type_id:
                record.user_id = record._assign_user()
            
            # Create calendar event
            if record.start:
                record._create_calendar_event()
        
        return records

    def write(self, vals):
        result = super().write(vals)
        
        # Update calendar event if scheduling changed
        if any(key in vals for key in ['start', 'duration', 'state']):
            for record in self:
                if record.calendar_event_id:
                    record._update_calendar_event()
                elif record.start and record.state in ('scheduled', 'confirmed'):
                    record._create_calendar_event()
        
        return result

    # =====================
    # BUSINESS LOGIC
    # =====================
    def _assign_user(self):
        """Assign a user based on appointment type settings."""
        self.ensure_one()
        apt_type = self.appointment_type_id
        users = apt_type.user_ids
        
        if not users:
            return False
        
        # For 'chosen' method, user should already be set from form
        # If not set (shouldn't happen normally), fall back to first user
        if apt_type.assign_method == 'chosen':
            # User should be set by the booking form, but if not, use first
            return self.user_id.id if self.user_id else users[0].id
        
        if len(users) == 1 or apt_type.assign_method == 'specific':
            return users[0].id
        
        if apt_type.assign_method == 'random':
            import random
            return random.choice(users.ids)
        
        if apt_type.assign_method == 'round_robin':
            # Get last assigned user for this type
            last_booking = self.search([
                ('appointment_type_id', '=', apt_type.id),
                ('user_id', 'in', users.ids),
                ('id', '!=', self.id),
            ], order='create_date desc', limit=1)
            
            if last_booking and last_booking.user_id in users:
                # Get next user in rotation
                user_list = list(users.ids)
                current_index = user_list.index(last_booking.user_id.id)
                next_index = (current_index + 1) % len(user_list)
                return user_list[next_index]
            
            return users[0].id
        
        if apt_type.assign_method == 'least_busy':
            # Find user with least bookings in next 7 days
            now = fields.Datetime.now()
            week_later = now + timedelta(days=7)
            
            booking_counts = {}
            for user in users:
                count = self.search_count([
                    ('user_id', '=', user.id),
                    ('start', '>=', now),
                    ('start', '<=', week_later),
                    ('state', 'in', ['scheduled', 'confirmed']),
                ])
                booking_counts[user.id] = count
            
            return min(booking_counts, key=booking_counts.get)
        
        return users[0].id

    def _create_calendar_event(self):
        """Create a calendar event for this booking."""
        self.ensure_one()
        if not self.start or self.calendar_event_id:
            return
        
        partner_ids = [self.partner_id.id] if self.partner_id else []
        if self.user_id:
            partner_ids.append(self.user_id.partner_id.id)
        
        # Generate video link if needed
        video_link = self._generate_video_link()
        
        event_vals = {
            'name': f"{self.appointment_type_id.name} with {self.invitee_name}",
            'start': self.start,
            'stop': self.stop,
            'duration': self.duration,
            'partner_ids': [(6, 0, partner_ids)],
            'user_id': self.user_id.id if self.user_id else self.env.user.id,
            'location': self.location or self.appointment_type_id.location,
            'videocall_location': video_link,
            'description': self._get_event_description(),
            'alarm_ids': [(6, 0, self.appointment_type_id.alarm_ids.ids)],
            'categ_ids': [(6, 0, self.appointment_type_id.categ_ids.ids)],
        }
        
        self.calendar_event_id = self.env['calendar.event'].create(event_vals)
        self.video_link = video_link

    def _update_calendar_event(self):
        """Update the associated calendar event."""
        self.ensure_one()
        if not self.calendar_event_id:
            return
        
        if self.state == 'cancelled':
            self.calendar_event_id.unlink()
            return
        
        self.calendar_event_id.write({
            'start': self.start,
            'stop': self.stop,
            'duration': self.duration,
        })

    def _generate_video_link(self):
        """Generate video conference link based on settings."""
        self.ensure_one()
        apt_type = self.appointment_type_id
        
        if apt_type.location_type != 'online':
            return False
        
        if apt_type.video_conference_type == 'jitsi':
            room_id = str(uuid.uuid4())[:8]
            return f"https://meet.jit.si/odoo-{room_id}"
        
        if apt_type.video_conference_type == 'custom':
            return apt_type.video_conference_link
        
        return False

    def _get_event_description(self):
        """Generate calendar event description."""
        self.ensure_one()
        lines = []
        
        if self.appointment_type_id.description:
            lines.append(self.appointment_type_id.description)
        
        lines.append(f"\n<b>Invitee:</b> {self.invitee_name}")
        if self.invitee_email:
            lines.append(f"<b>Email:</b> {self.invitee_email}")
        if self.invitee_phone:
            lines.append(f"<b>Phone:</b> {self.invitee_phone}")
        
        # Add answers to questions
        if self.answer_ids:
            lines.append("\n<b>Responses:</b>")
            for answer in self.answer_ids:
                lines.append(f"<br/>• {answer.question_id.name}: {answer.value}")
        
        if self.notes:
            lines.append(f"\n<b>Notes:</b>\n{self.notes}")
        
        return '\n'.join(lines)

    # =====================
    # ACTIONS
    # =====================
    def action_confirm(self):
        """Confirm the booking and send all notifications."""
        for record in self:
            if record.state == 'pending' and record.start:
                record.state = 'scheduled'
            if record.state in ('pending', 'scheduled') and record.start:
                record.state = 'confirmed'
                # Send invitee confirmation
                record._send_confirmation_email()
                # Send host notification (new feature)
                record._send_host_notification()

    def action_cancel(self):
        """Cancel the booking and notify all parties."""
        for record in self:
            record.state = 'cancelled'
            record.cancel_date = fields.Datetime.now()
            if record.calendar_event_id:
                record.calendar_event_id.unlink()
            # Send invitee cancellation
            record._send_cancellation_email()
            # Send host cancellation notification
            record._send_host_cancellation_notification()

    def action_mark_completed(self):
        """Mark booking as completed."""
        for record in self:
            record.state = 'completed'

    def action_mark_no_show(self):
        """Mark as no-show."""
        for record in self:
            record.state = 'no_show'

    def action_reschedule(self):
        """Open reschedule wizard."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': self.reschedule_url,
            'target': 'new',
        }

    def action_open_calendar_event(self):
        """Open related calendar event."""
        self.ensure_one()
        if self.calendar_event_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'calendar.event',
                'res_id': self.calendar_event_id.id,
                'view_mode': 'form',
                'target': 'current',
            }

    def action_send_reminder(self):
        """Manually send reminder email."""
        self.ensure_one()
        self._send_reminder_email()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Reminder Sent'),
                'message': _('A reminder email has been sent to %s') % self.invitee_email,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_send_followup(self):
        """Manually send follow-up email."""
        self.ensure_one()
        self._send_followup_email()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Follow-up Sent'),
                'message': _('A follow-up email has been sent to %s') % self.invitee_email,
                'type': 'success',
                'sticky': False,
            }
        }

    # =====================
    # EMAIL METHODS
    # =====================
    def _send_confirmation_email(self):
        """Send booking confirmation email to invitee."""
        self.ensure_one()
        _logger.info(f"[APPOINTMENT] Starting confirmation email for booking {self.id}")
        _logger.info(f"[APPOINTMENT] Invitee: {self.invitee_name} <{self.invitee_email}>")
        _logger.info(f"[APPOINTMENT] Confirmation email enabled: {self.appointment_type_id.confirmation_email}")
        
        if not self.appointment_type_id.confirmation_email:
            _logger.warning(f"[APPOINTMENT] Confirmation email disabled for appointment type {self.appointment_type_id.name}")
            return
        
        template = self.env.ref('appointment.mail_template_booking_confirmation', raise_if_not_found=False)
        _logger.info(f"[APPOINTMENT] Template found: {template is not None}")
        if template:
            try:
                result = template.send_mail(self.id, force_send=True)
                _logger.info(f"[APPOINTMENT] Email sent successfully, mail ID: {result}")
            except Exception as e:
                _logger.error(f"[APPOINTMENT] Failed to send confirmation email: {str(e)}", exc_info=True)

    def _send_cancellation_email(self):
        """Send cancellation email to invitee."""
        self.ensure_one()
        template = self.env.ref('appointment.mail_template_booking_cancellation', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    def _send_reminder_email(self):
        """Send reminder email to invitee."""
        self.ensure_one()
        template = self.env.ref('appointment.mail_template_booking_reminder', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
            self.write({
                'reminder_sent': True,
                'reminder_sent_date': fields.Datetime.now(),
            })

    def _send_host_notification(self):
        """Send new booking notification to host."""
        self.ensure_one()
        if self.host_notified:
            return
        
        template = self.env.ref('appointment.mail_template_host_notification', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
            self.host_notified = True

    def _send_host_cancellation_notification(self):
        """Send cancellation notification to host."""
        self.ensure_one()
        template = self.env.ref('appointment.mail_template_host_cancellation', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    def _send_followup_email(self):
        """Send follow-up email to invitee after meeting."""
        self.ensure_one()
        if self.followup_sent:
            return
        
        if not self.appointment_type_id.follow_up_enabled:
            return
        
        template = self.env.ref('appointment.mail_template_booking_followup', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
            self.write({
                'followup_sent': True,
                'followup_sent_date': fields.Datetime.now(),
            })

    # =====================
    # CRON METHODS
    # =====================
    @api.model
    def _cron_send_reminders(self):
        """Cron job to send reminder emails with proper tracking."""
        now = fields.Datetime.now()
        
        # Only get bookings that haven't received reminders yet
        bookings = self.search([
            ('state', '=', 'confirmed'),
            ('start', '>', now),
            ('reminder_sent', '=', False),
        ])
        
        for booking in bookings:
            if not booking.appointment_type_id.reminder_enabled:
                continue
            
            reminder_time = booking.start - timedelta(hours=booking.appointment_type_id.reminder_hours)
            if now >= reminder_time:
                try:
                    booking._send_reminder_email()
                except Exception as e:
                    # Log error but continue processing other bookings
                    import logging
                    _logger = logging.getLogger(__name__)
                    _logger.error(f"Failed to send reminder for booking {booking.id}: {e}")

    @api.model
    def _cron_send_followups(self):
        """Cron job to send follow-up emails after meetings."""
        now = fields.Datetime.now()
        
        # Get completed bookings that haven't received follow-ups
        completed_bookings = self.search([
            ('state', '=', 'completed'),
            ('followup_sent', '=', False),
        ])
        
        for booking in completed_bookings:
            if not booking.appointment_type_id.follow_up_enabled:
                continue
            
            followup_time = booking.stop + timedelta(hours=booking.appointment_type_id.follow_up_hours)
            if now >= followup_time:
                try:
                    booking._send_followup_email()
                except Exception as e:
                    import logging
                    _logger = logging.getLogger(__name__)
                    _logger.error(f"Failed to send follow-up for booking {booking.id}: {e}")

    @api.model
    def _cron_mark_completed(self):
        """Cron job to auto-mark past appointments as completed."""
        now = fields.Datetime.now()
        
        past_bookings = self.search([
            ('state', '=', 'confirmed'),
            ('stop', '<', now),
        ])
        
        past_bookings.write({'state': 'completed'})

    # =====================
    # RECURRING BOOKING METHODS
    # =====================
    def create_recurring_bookings(self, pattern, count):
        """Create recurring booking instances."""
        self.ensure_one()
        
        if not self.start:
            return self
        
        intervals = {
            'daily': timedelta(days=1),
            'weekly': timedelta(weeks=1),
            'biweekly': timedelta(weeks=2),
            'monthly': relativedelta(months=1),
        }
        
        interval = intervals.get(pattern, timedelta(weeks=1))
        bookings = self
        
        self.write({
            'is_recurring': True,
            'recurring_pattern': pattern,
            'recurring_count': count,
            'recurring_index': 1,
        })
        
        for i in range(2, count + 1):
            if pattern == 'monthly':
                new_start = self.start + relativedelta(months=i-1)
            else:
                new_start = self.start + (interval * (i - 1))
            
            new_booking = self.copy({
                'start': new_start,
                'recurring_parent_id': self.id,
                'recurring_index': i,
                'is_recurring': True,
                'recurring_pattern': pattern,
                'recurring_count': count,
                'calendar_event_id': False,  # Will be created on confirm
            })
            bookings |= new_booking
        
        return bookings

    def action_cancel_recurring(self):
        """Cancel all recurring instances."""
        self.ensure_one()
        
        if self.recurring_parent_id:
            parent = self.recurring_parent_id
        else:
            parent = self
        
        # Cancel parent and all children
        (parent | parent.recurring_child_ids).action_cancel()

