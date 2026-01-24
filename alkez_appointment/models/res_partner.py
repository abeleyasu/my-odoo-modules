# Copyright 2024 Your Company
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    appointment_booking_ids = fields.One2many(
        'appointment.booking',
        'partner_id',
        string="Appointments"
    )
    
    appointment_count = fields.Integer(
        compute="_compute_appointment_count"
    )

    def _compute_appointment_count(self):
        for partner in self:
            partner.appointment_count = len(partner.appointment_booking_ids)

    def action_view_appointments(self):
        """View all appointments for this partner."""
        self.ensure_one()
        return {
            'name': 'Appointments',
            'type': 'ir.actions.act_window',
            'res_model': 'appointment.booking',
            'view_mode': 'tree,form,calendar',
            'domain': [('partner_id', '=', self.id)],
        }
