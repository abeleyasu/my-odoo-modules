# Copyright 2024 Your Company
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class AppointmentSlot(models.Model):
    _name = "appointment.slot"
    _description = "Appointment Time Slot"
    _order = "weekday, start_hour"

    appointment_type_id = fields.Many2one(
        'appointment.type',
        string="Appointment Type",
        required=True,
        ondelete='cascade'
    )
    
    weekday = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday'),
    ], string="Day", required=True)
    
    start_hour = fields.Float(string="From", required=True)
    end_hour = fields.Float(string="To", required=True)
