# Copyright 2024 Your Company
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class AppointmentTypeAvailability(models.Model):
    """Weekly availability schedule for appointment types"""
    _name = "appointment.type.availability"
    _description = "Appointment Type Availability"
    _order = "weekday, start_hour"

    appointment_type_id = fields.Many2one(
        "appointment.type",
        string="Appointment Type",
        required=True,
        ondelete="cascade",
    )
    weekday = fields.Selection(
        [
            ("0", "Monday"),
            ("1", "Tuesday"),
            ("2", "Wednesday"),
            ("3", "Thursday"),
            ("4", "Friday"),
            ("5", "Saturday"),
            ("6", "Sunday"),
        ],
        string="Day of Week",
        required=True,
        default="0",
    )
    start_hour = fields.Float(
        string="Start Time",
        required=True,
        default=9.0,
        help="Start time in 24-hour format (e.g., 9.0 = 9:00 AM)",
    )
    end_hour = fields.Float(
        string="End Time",
        required=True,
        default=17.0,
        help="End time in 24-hour format (e.g., 17.0 = 5:00 PM)",
    )

    @api.constrains("start_hour", "end_hour")
    def _check_hours(self):
        for record in self:
            if record.start_hour >= record.end_hour:
                from odoo.exceptions import ValidationError
                raise ValidationError("End time must be after start time.")
            if record.start_hour < 0 or record.end_hour > 24:
                from odoo.exceptions import ValidationError
                raise ValidationError("Hours must be between 0 and 24.")


class AppointmentTypeException(models.Model):
    """Date-specific exceptions for availability (blocked dates or special hours)"""
    _name = "appointment.type.exception"
    _description = "Appointment Date Exception"
    _order = "date"

    appointment_type_id = fields.Many2one(
        "appointment.type",
        string="Appointment Type",
        required=True,
        ondelete="cascade",
    )
    date = fields.Date(
        string="Date",
        required=True,
    )
    exception_type = fields.Selection(
        [
            ("blocked", "Blocked (No Availability)"),
            ("special", "Special Hours"),
        ],
        string="Type",
        required=True,
        default="blocked",
    )
    start_hour = fields.Float(
        string="Start Time",
        default=9.0,
        help="Only used for special hours",
    )
    end_hour = fields.Float(
        string="End Time",
        default=17.0,
        help="Only used for special hours",
    )
    reason = fields.Char(
        string="Reason",
        help="Optional reason for this exception",
    )

    @api.constrains("start_hour", "end_hour", "exception_type")
    def _check_hours(self):
        for record in self:
            if record.exception_type == "special":
                if record.start_hour >= record.end_hour:
                    from odoo.exceptions import ValidationError
                    raise ValidationError("End time must be after start time.")
