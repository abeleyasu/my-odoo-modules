# Copyright 2024 Your Company
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import uuid
from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    appointment_slug = fields.Char(
        string="Appointment URL Slug",
        compute="_compute_appointment_slug",
        store=True,
        readonly=False,
        help="Custom URL for your appointment page"
    )
    
    appointment_type_ids = fields.Many2many(
        'appointment.type',
        string="My Event Types"
    )
    
    appointment_booking_ids = fields.One2many(
        'appointment.booking',
        'user_id',
        string="My Appointments"
    )
    
    # Branding relation
    appointment_branding_id = fields.Many2one(
        'appointment.branding',
        string="Branding",
        compute="_compute_branding",
    )
    
    # Calendar sync
    appointment_calendar_sync_ids = fields.One2many(
        'appointment.calendar.sync',
        'user_id',
        string="Calendar Syncs"
    )
    
    # Calendly-like profile settings
    appointment_welcome_message = fields.Html(
        string="Welcome Message",
        translate=True,
        help="Shown on your appointment page"
    )
    
    appointment_bio = fields.Text(
        string="Bio",
        help="Short description shown to invitees"
    )
    
    appointment_timezone = fields.Selection(
        '_get_timezone_selection',
        string="Appointment Timezone",
        default='UTC'
    )

    @api.depends('name', 'login')
    def _compute_appointment_slug(self):
        for user in self:
            if not user.appointment_slug:
                # Generate slug from name or login
                base = user.name or user.login or 'user'
                slug = base.lower().replace(' ', '-')
                slug = ''.join(c for c in slug if c.isalnum() or c == '-')
                # Ensure uniqueness
                existing = self.search([
                    ('appointment_slug', '=', slug),
                    ('id', '!=', user.id)
                ], limit=1)
                if existing:
                    slug = f"{slug}-{str(uuid.uuid4())[:4]}"
                user.appointment_slug = slug

    @api.model
    def _get_timezone_selection(self):
        """Get list of timezones."""
        import pytz
        return [(tz, tz) for tz in pytz.common_timezones]

    def _compute_branding(self):
        """Get or create branding for user"""
        for user in self:
            branding = self.env['appointment.branding'].search([
                ('user_id', '=', user.id)
            ], limit=1)
            user.appointment_branding_id = branding.id if branding else False

    def get_branding(self):
        """Get branding settings, creating default if needed"""
        self.ensure_one()
        return self.env['appointment.branding'].get_branding_for_user(self.id)

    def get_public_appointment_url(self):
        """Get public appointment page URL."""
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base_url}/appointment/{self.appointment_slug}"

    def action_view_appointments(self):
        """View all appointments for this user."""
        self.ensure_one()
        return {
            'name': 'My Appointments',
            'type': 'ir.actions.act_window',
            'res_model': 'appointment.booking',
            'view_mode': 'calendar,tree,form',
            'domain': [('user_id', '=', self.id)],
            'context': {'default_user_id': self.id},
        }
