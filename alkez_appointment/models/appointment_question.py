# Copyright 2024 Your Company
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models, _


class AppointmentQuestion(models.Model):
    _name = "appointment.question"
    _description = "Appointment Question"
    _order = "sequence, id"

    appointment_type_id = fields.Many2one(
        'appointment.type',
        string="Appointment Type",
        required=True,
        ondelete='cascade'
    )
    
    name = fields.Char(
        string="Question",
        required=True,
        translate=True
    )
    
    sequence = fields.Integer(default=10)
    
    question_type = fields.Selection([
        ('text', 'Single Line Text'),
        ('textarea', 'Multi Line Text'),
        ('select', 'Dropdown'),
        ('radio', 'Radio Buttons'),
        ('checkbox', 'Checkboxes'),
        ('phone', 'Phone Number'),
        ('email', 'Email'),
    ], string="Type", default='text', required=True)
    
    placeholder = fields.Char(string="Placeholder")
    
    required = fields.Boolean(
        string="Required",
        default=False
    )
    
    # For select/radio/checkbox types
    options = fields.Text(
        string="Options",
        help="One option per line"
    )
    
    @api.depends('name')
    def _compute_display_name(self):
        for record in self:
            record.display_name = record.name
    
    def get_options_list(self):
        """Return options as a list."""
        self.ensure_one()
        if not self.options:
            return []
        return [opt.strip() for opt in self.options.split('\n') if opt.strip()]
