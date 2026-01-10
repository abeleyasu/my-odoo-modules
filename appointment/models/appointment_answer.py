# Copyright 2024 Your Company
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models, _


class AppointmentAnswer(models.Model):
    _name = "appointment.answer"
    _description = "Appointment Answer"
    _order = "question_id"

    booking_id = fields.Many2one(
        'appointment.booking',
        string="Booking",
        required=True,
        ondelete='cascade',
    )
    
    question_id = fields.Many2one(
        'appointment.question',
        string="Question",
        required=True,
        ondelete='cascade',
    )
    
    # Stored fields matching database schema
    value_text = fields.Text(string="Text Answer")
    value_select = fields.Char(string="Selected Option")
    
    # Computed convenience field that returns the appropriate value
    value = fields.Text(
        string="Answer",
        compute="_compute_value",
        inverse="_inverse_value",
        store=False
    )
    
    @api.depends('value_text', 'value_select')
    def _compute_value(self):
        for record in self:
            # Return value_text if set, otherwise value_select
            record.value = record.value_text or record.value_select or ''
    
    def _inverse_value(self):
        for record in self:
            # Store in value_text by default
            record.value_text = record.value
    
    @api.depends('question_id', 'value')
    def _compute_display_name(self):
        for record in self:
            question_name = record.question_id.name if record.question_id else "Question"
            record.display_name = f"{question_name}: {record.value or _('No answer')}"
