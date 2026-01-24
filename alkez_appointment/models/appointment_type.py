# Copyright 2024 Your Company
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import uuid
import pytz
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import format_duration


class AppointmentType(models.Model):
    _name = "appointment.type"
    _description = "Appointment Type"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence, name"

    # =====================
    # BASIC FIELDS
    # =====================
    name = fields.Char(
        string="Event Name",
        required=True,
        translate=True,
        tracking=True,
        help="Name displayed to invitees (e.g., '30 Minute Meeting', 'Product Demo')"
    )
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    
    # URL and Access
    slug = fields.Char(
        string="URL Slug",
        compute="_compute_slug",
        store=True,
        readonly=False,
        help="Custom URL path for this event type"
    )
    access_token = fields.Char(
        string="Access Token",
        default=lambda self: str(uuid.uuid4()),
        copy=False
    )
    
    # =====================
    # DURATION & SCHEDULING
    # =====================
    duration = fields.Float(
        string="Duration",
        required=True,
        default=0.5,
        help="Meeting duration in hours"
    )
    duration_display = fields.Char(
        compute="_compute_duration_display",
        string="Duration Display"
    )
    
    slot_duration = fields.Float(
        string="Time Slot Interval",
        default=0.25,  # 15 minutes
        help="Interval between available time slots (e.g., 15 min, 30 min)"
    )
    
    # Buffer times (Calendly feature)
    buffer_time_before = fields.Float(
        string="Buffer Before",
        default=0,
        help="Buffer time before each meeting in hours"
    )
    buffer_time_after = fields.Float(
        string="Buffer After",
        default=0,
        help="Buffer time after each meeting in hours"
    )
    
    # Scheduling limits
    min_schedule_notice = fields.Float(
        string="Minimum Notice",
        default=4.0,
        help="Minimum hours before appointment can be scheduled"
    )
    max_schedule_days = fields.Integer(
        string="Maximum Days in Advance",
        default=60,
        help="How far in the future appointments can be scheduled"
    )
    
    # Daily/Weekly limits
    max_bookings_per_day = fields.Integer(
        string="Max Bookings Per Day",
        default=0,
        help="Maximum bookings per day (0 = unlimited)"
    )
    
    # =====================
    # GROUP BOOKINGS
    # =====================
    allow_group_booking = fields.Boolean(
        string="Allow Group Booking",
        default=False,
        help="Allow multiple attendees to book the same slot"
    )
    max_attendees = fields.Integer(
        string="Maximum Attendees",
        default=1,
        help="Maximum number of attendees per slot (1 = individual booking)"
    )
    min_attendees = fields.Integer(
        string="Minimum Attendees",
        default=1,
        help="Minimum attendees required for booking to proceed"
    )
    show_remaining_seats = fields.Boolean(
        string="Show Remaining Seats",
        default=True,
        help="Display how many spots are left on the booking page"
    )
    
    # =====================
    # RECURRING APPOINTMENTS
    # =====================
    allow_recurring = fields.Boolean(
        string="Allow Recurring",
        default=False,
        help="Allow invitees to book recurring appointments"
    )
    recurring_max_occurrences = fields.Integer(
        string="Max Occurrences",
        default=10,
        help="Maximum number of recurring appointments"
    )
    recurring_patterns = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('biweekly', 'Every 2 Weeks'),
        ('monthly', 'Monthly'),
    ], string="Recurring Pattern", default='weekly')
    
    # =====================
    # AVAILABILITY
    # =====================
    schedule_type = fields.Selection([
        ('custom', 'Custom Schedule'),
        ('resource_calendar', 'Working Hours'),
    ], string="Availability Type", default='custom', required=True)
    
    resource_calendar_id = fields.Many2one(
        'resource.calendar',
        string="Working Hours",
        help="Use this calendar for availability"
    )
    
    # Custom availability (Calendly-like)
    availability_ids = fields.One2many(
        'appointment.type.availability',
        'appointment_type_id',
        string="Availability Rules"
    )
    
    # Date exceptions (blocked dates or special hours)
    exception_ids = fields.One2many(
        'appointment.type.exception',
        'appointment_type_id',
        string="Date Exceptions",
        help="Block specific dates or set special hours"
    )
    
    # =====================
    # LOCATION
    # =====================
    location_type = fields.Selection([
        ('online', 'Video Conference'),
        ('in_person', 'In-Person Meeting'),
        ('phone_incoming', 'Phone Call - Invitee Calls'),
        ('phone_outgoing', 'Phone Call - I Call Invitee'),
        ('custom', 'Custom Location'),
    ], string="Location Type", default='online', required=True)
    
    location = fields.Char(
        string="Location",
        help="Physical address or custom location description"
    )
    video_conference_type = fields.Selection([
        ('jitsi', 'Jitsi Meet'),
        ('google_meet', 'Google Meet'),
        ('zoom', 'Zoom'),
        ('teams', 'Microsoft Teams'),
        ('custom', 'Custom Link'),
    ], string="Video Conference", default='jitsi')
    
    video_conference_link = fields.Char(string="Custom Video Link")
    
    # =====================
    # ASSIGNMENT
    # =====================
    assign_method = fields.Selection([
        ('chosen', 'Let Invitee Choose'),
        ('round_robin', 'Round Robin'),
        ('least_busy', 'Least Busy'),
        ('random', 'Random'),
        ('specific', 'Specific User'),
    ], string="Assignment Method", default='specific', required=True)
    
    user_ids = fields.Many2many(
        'res.users',
        string="Team Members",
        domain=[('share', '=', False)],
        required=True,
        help="Users who can receive appointments"
    )
    
    @api.constrains('user_ids')
    def _check_user_ids(self):
        """Ensure at least one user is assigned."""
        for record in self:
            if not record.user_ids:
                raise ValidationError(_("At least one team member must be assigned to this appointment type."))
    
    # =====================
    # QUESTIONS & FORMS
    # =====================
    question_ids = fields.One2many(
        'appointment.question',
        'appointment_type_id',
        string="Questions"
    )
    
    require_email = fields.Boolean(default=True)
    require_phone = fields.Boolean(default=False)
    require_name = fields.Boolean(default=True)
    
    # =====================
    # BRANDING & APPEARANCE
    # =====================
    color = fields.Char(
        string="Brand Color",
        default="#0069ff",
        help="Primary color for the booking page"
    )
    
    description = fields.Html(
        string="Description",
        translate=True,
        help="Description shown on the booking page"
    )
    
    image = fields.Binary(string="Event Image", attachment=True)
    
    # Display settings
    show_avatar = fields.Boolean(string="Show Host Avatar", default=True)
    show_timezone_selector = fields.Boolean(string="Show Timezone Selector", default=True)
    
    # =====================
    # NOTIFICATIONS
    # =====================
    confirmation_email = fields.Boolean(
        string="Send Confirmation Email",
        default=True
    )
    reminder_enabled = fields.Boolean(
        string="Send Reminders",
        default=True
    )
    reminder_hours = fields.Float(
        string="Reminder Time",
        default=24,
        help="Hours before meeting to send reminder"
    )
    
    follow_up_enabled = fields.Boolean(
        string="Send Follow-up",
        default=False
    )
    follow_up_hours = fields.Float(
        string="Follow-up Time",
        default=24,
        help="Hours after meeting to send follow-up"
    )
    
    # Custom messages
    confirmation_message = fields.Html(
        string="Confirmation Message",
        translate=True,
        help="Custom message on the confirmation page"
    )
    
    # =====================
    # CALENDAR SETTINGS
    # =====================
    alarm_ids = fields.Many2many(
        'calendar.alarm',
        string="Default Reminders"
    )
    categ_ids = fields.Many2many(
        'calendar.event.type',
        string="Tags"
    )
    
    # =====================
    # COUNTERS
    # =====================
    booking_count = fields.Integer(
        compute="_compute_booking_count"
    )
    upcoming_booking_count = fields.Integer(
        compute="_compute_booking_count"
    )
    invite_count = fields.Integer(
        compute="_compute_invite_count"
    )
    
    # =====================
    # COMPUTED FIELDS
    # =====================
    public_url = fields.Char(
        compute="_compute_public_url",
        string="Public URL"
    )
    embed_code_inline = fields.Text(
        compute="_compute_embed_codes",
        string="Inline Embed Code"
    )
    embed_code_popup = fields.Text(
        compute="_compute_embed_codes",
        string="Popup Widget Embed Code"
    )
    embed_code_text = fields.Text(
        compute="_compute_embed_codes",
        string="Popup Text Embed Code"
    )

    @api.depends('name')
    def _compute_slug(self):
        for record in self:
            if record.name:
                slug = record.name.lower()
                slug = ''.join(c if c.isalnum() else '-' for c in slug)
                slug = '-'.join(filter(None, slug.split('-')))
                record.slug = slug[:50]
            elif not record.slug:
                record.slug = ''
    
    @api.onchange('slug')
    def _onchange_slug(self):
        """Ensure slug is always URL-safe."""
        if self.slug:
            slug = self.slug.lower()
            slug = ''.join(c if c.isalnum() else '-' for c in slug)
            slug = '-'.join(filter(None, slug.split('-')))
            self.slug = slug[:50]
    
    @api.model_create_multi
    def create(self, vals_list):
        """Ensure slug is URL-safe on create."""
        for vals in vals_list:
            if vals.get('slug'):
                slug = vals['slug'].lower()
                slug = ''.join(c if c.isalnum() else '-' for c in slug)
                slug = '-'.join(filter(None, slug.split('-')))
                vals['slug'] = slug[:50]
        return super().create(vals_list)
    
    def write(self, vals):
        """Ensure slug is URL-safe on write."""
        if vals.get('slug'):
            slug = vals['slug'].lower()
            slug = ''.join(c if c.isalnum() else '-' for c in slug)
            slug = '-'.join(filter(None, slug.split('-')))
            vals['slug'] = slug[:50]
        return super().write(vals)

    @api.depends('duration')
    def _compute_duration_display(self):
        for record in self:
            minutes = int(record.duration * 60)
            if minutes >= 60:
                hours = minutes // 60
                mins = minutes % 60
                if mins:
                    record.duration_display = f"{hours}h {mins}min"
                else:
                    record.duration_display = f"{hours} hour{'s' if hours > 1 else ''}"
            else:
                record.duration_display = f"{minutes} min"

    def _compute_booking_count(self):
        for record in self:
            bookings = self.env['appointment.booking'].search([
                ('appointment_type_id', '=', record.id)
            ])
            record.booking_count = len(bookings)
            record.upcoming_booking_count = len(bookings.filtered(
                lambda b: b.start and b.start > fields.Datetime.now() and b.state == 'confirmed'
            ))

    def _compute_invite_count(self):
        for record in self:
            record.invite_count = self.env['appointment.invite'].search_count([
                ('appointment_type_ids', 'in', record.id)
            ])

    def _compute_public_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for record in self:
            if record.user_ids:
                user = record.user_ids[0]
                if user.appointment_slug:
                    record.public_url = f"{base_url}/appointment/{user.appointment_slug}/{record.slug}"
                else:
                    # Fallback if user doesn't have slug
                    record.public_url = f"{base_url}/appointment/type/{record.id}"
            else:
                # No users assigned - show placeholder
                record.public_url = f"{base_url}/appointment/type/{record.id}"

    def _compute_embed_codes(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for record in self:
            url = record.public_url
            embed_script_url = f"{base_url}/appointment/embed/script.js"
            
            # Inline embed - Simple iframe approach
            record.embed_code_inline = f'''<!-- Appointment Inline Widget Begin -->
<div id="appointment-widget-{record.id}" style="min-width:320px;height:700px;border:none;">
    <iframe src="{url}?embed=1" style="width:100%;height:100%;border:none;" loading="lazy"></iframe>
</div>
<!-- Appointment Inline Widget End -->'''

            # Popup widget - Button that opens modal
            record.embed_code_popup = f'''<!-- Appointment Popup Widget Begin -->
<style>
.appointment-popup-btn {{
    display: inline-flex; align-items: center; padding: 14px 28px;
    background: {record.color or '#0069ff'}; color: #ffffff; border: none; border-radius: 40px;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 15px; font-weight: 600; cursor: pointer; text-decoration: none;
    box-shadow: 0 4px 16px rgba(0, 105, 255, 0.35); transition: all 0.2s ease;
}}
.appointment-popup-btn:hover {{ transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0, 105, 255, 0.4); }}
.appointment-modal {{ position: fixed; inset: 0; z-index: 999999; display: none; align-items: center; justify-content: center; background: rgba(0,0,0,0.5); }}
.appointment-modal.active {{ display: flex; }}
.appointment-modal-content {{ position: relative; background: #fff; border-radius: 12px; max-width: 1000px; width: 95%; max-height: 90vh; overflow: hidden; }}
.appointment-modal-close {{ position: absolute; top: 10px; right: 10px; width: 36px; height: 36px; border: none; border-radius: 50%; background: rgba(0,0,0,0.1); cursor: pointer; font-size: 20px; }}
</style>
<button class="appointment-popup-btn" onclick="document.getElementById('apt-modal-{record.id}').classList.add('active')">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:8px">
        <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
        <line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line>
        <line x1="3" y1="10" x2="21" y2="10"></line>
    </svg>
    Schedule time with me
</button>
<div id="apt-modal-{record.id}" class="appointment-modal" onclick="if(event.target===this)this.classList.remove('active')">
    <div class="appointment-modal-content">
        <button class="appointment-modal-close" onclick="this.closest('.appointment-modal').classList.remove('active')">&times;</button>
        <iframe src="{url}?embed=1" style="width:100%;height:80vh;border:none;" loading="lazy"></iframe>
    </div>
</div>
<!-- Appointment Popup Widget End -->'''

            # Popup text - Simple link that opens modal
            record.embed_code_text = f'''<!-- Appointment Text Link Begin -->
<style>
.appointment-modal {{ position: fixed; inset: 0; z-index: 999999; display: none; align-items: center; justify-content: center; background: rgba(0,0,0,0.5); }}
.appointment-modal.active {{ display: flex; }}
.appointment-modal-content {{ position: relative; background: #fff; border-radius: 12px; max-width: 1000px; width: 95%; max-height: 90vh; overflow: hidden; }}
.appointment-modal-close {{ position: absolute; top: 10px; right: 10px; width: 36px; height: 36px; border: none; border-radius: 50%; background: rgba(0,0,0,0.1); cursor: pointer; font-size: 20px; }}
</style>
<a href="#" onclick="document.getElementById('apt-text-modal-{record.id}').classList.add('active');return false;" style="color:#0069ff;font-weight:500;">Schedule a meeting</a>
<div id="apt-text-modal-{record.id}" class="appointment-modal" onclick="if(event.target===this)this.classList.remove('active')">
    <div class="appointment-modal-content">
        <button class="appointment-modal-close" onclick="this.closest('.appointment-modal').classList.remove('active')">&times;</button>
        <iframe src="{url}?embed=1" style="width:100%;height:80vh;border:none;" loading="lazy"></iframe>
    </div>
</div>
<!-- Appointment Text Link End -->'''

    # =====================
    # METHODS
    # =====================
    def get_available_slots(self, user_id=None, start_date=None, end_date=None, timezone='UTC'):
        """Get available time slots for booking."""
        self.ensure_one()
        
        if not start_date:
            start_date = fields.Date.context_today(self)
        if not end_date:
            end_date = start_date + relativedelta(days=self.max_schedule_days)
        
        # Get the user(s) to check availability
        users = self.user_ids
        if user_id:
            users = self.env['res.users'].browse(user_id)
        
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        min_notice_time = now + timedelta(hours=self.min_schedule_notice)
        
        slots = {}
        current_date = start_date
        
        while current_date <= end_date:
            day_slots = self._get_day_slots(current_date, users, tz, min_notice_time)
            if day_slots:
                slots[current_date.isoformat()] = day_slots
            current_date += timedelta(days=1)
        
        return slots

    def _get_day_slots(self, date, users, tz, min_notice_time):
        """Get available slots for a specific day."""
        slots = []
        slot_duration = timedelta(hours=self.slot_duration)
        meeting_duration = timedelta(hours=self.duration)
        buffer_before = timedelta(hours=self.buffer_time_before)
        buffer_after = timedelta(hours=self.buffer_time_after)
        
        # Get working hours for the day
        work_intervals = self._get_work_intervals(date, users, tz)
        
        for start, end in work_intervals:
            current = start
            while current + meeting_duration <= end:
                slot_start = current
                slot_end = current + meeting_duration
                
                # Check minimum notice
                if slot_start < min_notice_time:
                    current += slot_duration
                    continue
                
                # Check if slot is available (no conflicts)
                if self._is_slot_available(slot_start, slot_end, users, buffer_before, buffer_after):
                    slot_data = {
                        'start': slot_start.isoformat(),
                        'end': slot_end.isoformat(),
                        'start_formatted': slot_start.strftime('%I:%M %p'),
                    }
                    
                    # Add remaining seats for group booking
                    if self.allow_group_booking and self.show_remaining_seats:
                        remaining = self._get_remaining_seats(slot_start, slot_end, users)
                        slot_data['remaining_seats'] = remaining
                        slot_data['max_attendees'] = self.max_attendees
                    
                    slots.append(slot_data)
                
                current += slot_duration
        
        return slots
    
    def _get_remaining_seats(self, start, end, users):
        """Calculate remaining seats for a group booking slot."""
        # Convert to UTC for database comparison
        if start.tzinfo is not None:
            start_utc = start.astimezone(pytz.UTC).replace(tzinfo=None)
            end_utc = end.astimezone(pytz.UTC).replace(tzinfo=None)
        else:
            start_utc = start
            end_utc = end
        
        # Count existing bookings for this exact slot
        slot_bookings = self.env['appointment.booking'].search_count([
            ('appointment_type_id', '=', self.id),
            ('user_id', 'in', users.ids),
            ('state', 'in', ['confirmed', 'scheduled']),
            ('start', '=', start_utc),
            ('stop', '=', end_utc),
        ])
        
        return max(0, self.max_attendees - slot_bookings)

    def _get_work_intervals(self, date, users, tz):
        """Get working intervals for a specific date, accounting for exceptions."""
        # First check if this date is blocked
        blocked_exception = self.exception_ids.filtered(
            lambda e: e.date == date and e.exception_type == 'blocked'
        )
        if blocked_exception:
            return []  # No availability on blocked dates
        
        # Check for special hours on this date
        special_exception = self.exception_ids.filtered(
            lambda e: e.date == date and e.exception_type == 'special'
        )
        
        if special_exception:
            # Use special hours instead of regular schedule
            intervals = []
            for exc in special_exception:
                start_time = datetime.combine(date, datetime.min.time()) + timedelta(hours=exc.start_hour)
                end_time = datetime.combine(date, datetime.min.time()) + timedelta(hours=exc.end_hour)
                intervals.append((tz.localize(start_time), tz.localize(end_time)))
            return intervals
        
        # Regular schedule
        intervals = []
        
        if self.schedule_type == 'resource_calendar' and self.resource_calendar_id:
            # Use resource calendar
            start_dt = tz.localize(datetime.combine(date, datetime.min.time()))
            end_dt = tz.localize(datetime.combine(date, datetime.max.time()))
            
            work_intervals = self.resource_calendar_id._work_intervals_batch(
                start_dt.astimezone(pytz.utc),
                end_dt.astimezone(pytz.utc)
            )[False]
            
            for start, end, meta in work_intervals:
                intervals.append((start.astimezone(tz), end.astimezone(tz)))
        else:
            # Use custom availability
            weekday = date.weekday()
            for avail in self.availability_ids.filtered(lambda a: int(a.weekday) == weekday):
                start_time = datetime.combine(date, datetime.min.time()) + timedelta(hours=avail.start_hour)
                end_time = datetime.combine(date, datetime.min.time()) + timedelta(hours=avail.end_hour)
                intervals.append((tz.localize(start_time), tz.localize(end_time)))
        
        return intervals

    def _is_slot_available(self, start, end, users, buffer_before, buffer_after):
        """Check if a time slot is available (no conflicts)."""
        # Check for existing bookings
        check_start = start - buffer_before
        check_end = end + buffer_after
        
        # Convert to UTC for database comparison (Odoo stores datetimes in UTC)
        if check_start.tzinfo is not None:
            check_start_utc = check_start.astimezone(pytz.UTC).replace(tzinfo=None)
            check_end_utc = check_end.astimezone(pytz.UTC).replace(tzinfo=None)
            start_utc = start.astimezone(pytz.UTC).replace(tzinfo=None)
            end_utc = end.astimezone(pytz.UTC).replace(tzinfo=None)
        else:
            check_start_utc = check_start
            check_end_utc = check_end
            start_utc = start
            end_utc = end
        
        for user in users:
            # Check calendar events
            conflicting = self.env['calendar.event'].search([
                ('partner_ids', 'in', [user.partner_id.id]),
                ('start', '<', check_end_utc),
                ('stop', '>', check_start_utc),
            ], limit=1)
            
            if conflicting:
                return False
            
            # Check appointment bookings
            if self.allow_group_booking:
                # For group bookings, count existing bookings for this exact slot
                slot_bookings = self.env['appointment.booking'].search_count([
                    ('appointment_type_id', '=', self.id),
                    ('user_id', '=', user.id),
                    ('state', 'in', ['confirmed', 'scheduled']),
                    ('start', '=', start_utc),
                    ('stop', '=', end_utc),
                ])
                
                if slot_bookings >= self.max_attendees:
                    return False
            else:
                # For individual bookings, check for any overlap
                conflicting_bookings = self.env['appointment.booking'].search([
                    ('user_id', '=', user.id),
                    ('state', 'in', ['confirmed', 'scheduled']),
                    ('start', '<', check_end_utc),
                    ('stop', '>', check_start_utc),
                ], limit=1)
                
                if conflicting_bookings:
                    return False
        
        # Check daily booking limit
        if self.max_bookings_per_day > 0:
            day_start = start_utc.replace(hour=0, minute=0, second=0)
            day_end = start_utc.replace(hour=23, minute=59, second=59)
            
            day_bookings = self.env['appointment.booking'].search_count([
                ('appointment_type_id', '=', self.id),
                ('state', 'in', ['confirmed', 'scheduled']),
                ('start', '>=', day_start),
                ('start', '<=', day_end),
            ])
            
            if day_bookings >= self.max_bookings_per_day:
                return False
        
        return True

    def action_view_bookings(self):
        """Open bookings list."""
        self.ensure_one()
        return {
            'name': _('Bookings'),
            'type': 'ir.actions.act_window',
            'res_model': 'appointment.booking',
            'view_mode': 'calendar,tree,form',
            'domain': [('appointment_type_id', '=', self.id)],
            'context': {'default_appointment_type_id': self.id},
        }

    def action_open_public_url(self):
        """Open public booking page."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': self.public_url,
            'target': 'new',
        }

    def action_copy_embed_code(self):
        """Copy embed code action - shows a dialog with embed codes."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Embed Code'),
                'message': _('Check the Embed & Share tab for embed codes.'),
                'type': 'info',
                'sticky': False,
            }
        }
