# Copyright 2024 Your Company
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models, _


class AppointmentShare(models.TransientModel):
    """Wizard to share appointment booking page."""
    
    _name = 'appointment.share'
    _description = 'Share Appointment Booking Page'

    appointment_type_id = fields.Many2one(
        'appointment.type',
        string='Event Type',
        required=True,
        default=lambda self: self.env.context.get('default_appointment_type_id'),
    )
    
    share_link = fields.Char(
        string='Share Link',
        compute='_compute_share_link',
    )
    
    embed_code_inline = fields.Text(
        string='Inline Embed Code',
        compute='_compute_share_link',
    )
    
    embed_code_popup = fields.Text(
        string='Popup Embed Code',
        compute='_compute_share_link',
    )
    
    @api.depends('appointment_type_id')
    def _compute_share_link(self):
        for wizard in self:
            if wizard.appointment_type_id:
                wizard.share_link = wizard.appointment_type_id.public_url
                wizard.embed_code_inline = wizard.appointment_type_id.embed_code_inline
                wizard.embed_code_popup = wizard.appointment_type_id.embed_code_popup
            else:
                wizard.share_link = False
                wizard.embed_code_inline = False
                wizard.embed_code_popup = False
    
    def action_copy_link(self):
        """Copy sharing link to clipboard (through JS)."""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Link Copied'),
                'message': _('The booking link has been copied to your clipboard.'),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_send_by_email(self):
        """Open email composer to share the appointment link."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Share Appointment'),
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_body': _(
                    'You can book an appointment with me using this link: %s',
                    self.share_link
                ),
                'default_subject': _('Book an Appointment'),
            }
        }
