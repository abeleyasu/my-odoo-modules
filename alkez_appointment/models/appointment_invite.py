# Copyright 2024 Your Company
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import uuid
from datetime import datetime, timedelta

from odoo import api, fields, models, _


class AppointmentInvite(models.Model):
    _name = "appointment.invite"
    _description = "Appointment Invitation"
    _inherit = ["mail.thread"]
    _order = "create_date desc"

    name = fields.Char(
        string="Subject",
        required=True,
        default=lambda self: _("You're invited to schedule an appointment")
    )
    
    appointment_type_id = fields.Many2one(
        'appointment.type',
        string="Event Type",
        required=True
    )
    
    user_id = fields.Many2one(
        'res.users',
        string="Host",
        default=lambda self: self.env.user
    )
    
    # Invitee
    partner_id = fields.Many2one(
        'res.partner',
        string="Invitee"
    )
    invitee_email = fields.Char(string="Invitee Email")
    invitee_name = fields.Char(string="Invitee Name")
    
    # Access
    access_token = fields.Char(
        default=lambda self: str(uuid.uuid4()),
        copy=False
    )
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('scheduled', 'Scheduled'),
        ('expired', 'Expired'),
    ], string="Status", default='draft', tracking=True)
    
    expires_at = fields.Datetime(
        string="Expires At",
        default=lambda self: fields.Datetime.now() + timedelta(days=14)
    )
    
    # Resulting booking
    booking_id = fields.Many2one(
        'appointment.booking',
        string="Booking",
        readonly=True
    )
    
    # Custom message
    message = fields.Html(
        string="Personal Message",
        help="Add a personal note to the invitation email"
    )
    
    # URLs
    invite_url = fields.Char(
        compute="_compute_invite_url"
    )

    def _compute_invite_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for record in self:
            record.invite_url = f"{base_url}/appointment/invite/{record.access_token}"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('partner_id') and not vals.get('invitee_email'):
                partner = self.env['res.partner'].browse(vals['partner_id'])
                vals['invitee_email'] = partner.email
                vals['invitee_name'] = partner.name
        return super().create(vals_list)

    def action_send_invite(self):
        """Send invitation email."""
        for record in self:
            if record.state != 'draft':
                continue
            
            template = self.env.ref('appointment.mail_template_invite', raise_if_not_found=False)
            if template:
                template.send_mail(record.id, force_send=True)
            
            record.state = 'sent'
        
        return True

    def action_deactivate(self):
        """Deactivate the invitation."""
        self.ensure_one()
        self.state = 'expired'
        return True

    def action_copy_link(self):
        """Copy invite link - handled by JS."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Link Copied!'),
                'message': self.invite_url,
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model
    def _cron_expire_invites(self):
        """Mark expired invitations."""
        now = fields.Datetime.now()
        expired = self.search([
            ('state', '=', 'sent'),
            ('expires_at', '<', now),
        ])
        expired.write({'state': 'expired'})
