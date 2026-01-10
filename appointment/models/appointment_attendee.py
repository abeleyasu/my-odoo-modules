# Copyright 2024 Your Company
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class AppointmentBookingAttendee(models.Model):
    """Additional attendees for group bookings"""
    _name = "appointment.booking.attendee"
    _description = "Booking Attendee"
    _order = "sequence, id"

    booking_id = fields.Many2one(
        'appointment.booking',
        string="Booking",
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(default=10)
    
    # Attendee Information
    name = fields.Char(string="Name", required=True)
    email = fields.Char(string="Email", required=True)
    phone = fields.Char(string="Phone")
    
    # Partner link (optional)
    partner_id = fields.Many2one(
        'res.partner',
        string="Contact"
    )
    
    # Status
    confirmed = fields.Boolean(
        string="Confirmed",
        default=False,
        help="Whether attendee confirmed participation"
    )
    confirmation_token = fields.Char(string="Confirmation Token")
    
    @api.model_create_multi
    def create(self, vals_list):
        import uuid
        for vals in vals_list:
            if not vals.get('confirmation_token'):
                vals['confirmation_token'] = str(uuid.uuid4())
            
            # Find or create partner
            if vals.get('email') and not vals.get('partner_id'):
                partner = self.env['res.partner'].search([
                    ('email', '=ilike', vals['email'])
                ], limit=1)
                if not partner:
                    partner = self.env['res.partner'].create({
                        'name': vals.get('name', vals['email']),
                        'email': vals['email'],
                        'phone': vals.get('phone'),
                    })
                vals['partner_id'] = partner.id
        
        return super().create(vals_list)

    def action_confirm(self):
        """Confirm attendance"""
        self.write({'confirmed': True})
        return True

    def action_decline(self):
        """Decline attendance - remove from booking"""
        self.unlink()
        return True
