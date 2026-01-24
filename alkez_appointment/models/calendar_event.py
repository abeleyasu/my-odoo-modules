# Copyright 2024 Your Company
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    appointment_booking_id = fields.Many2one(
        'appointment.booking',
        string="Appointment Booking",
        ondelete='set null'
    )
    
    is_appointment = fields.Boolean(
        compute="_compute_is_appointment",
        store=True
    )

    def _compute_is_appointment(self):
        for record in self:
            record.is_appointment = bool(record.appointment_booking_id)
