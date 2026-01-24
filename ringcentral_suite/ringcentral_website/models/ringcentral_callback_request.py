# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class RingCentralCallbackRequest(models.Model):
    _name = 'ringcentral.callback.request'
    _description = 'Callback Request from Website'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Reference',
        default=lambda self: _('New'),
        readonly=True,
    )
    
    # Visitor Info
    visitor_name = fields.Char(string='Name', required=True)
    visitor_phone = fields.Char(string='Phone Number', required=True)
    visitor_email = fields.Char(string='Email')
    
    # Request Details
    subject = fields.Char(string='Subject')
    message = fields.Text(string='Message')
    preferred_time = fields.Selection([
        ('asap', 'As Soon As Possible'),
        ('morning', 'Morning (9am-12pm)'),
        ('afternoon', 'Afternoon (12pm-5pm)'),
        ('evening', 'Evening (5pm-8pm)'),
    ], string='Preferred Time', default='asap')
    
    preferred_date = fields.Date(string='Preferred Date')
    
    # Status
    state = fields.Selection([
        ('new', 'New'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='new', tracking=True)
    
    # Assignment
    assigned_user_id = fields.Many2one(
        'res.users',
        string='Assigned To',
        tracking=True,
    )
    
    # Related Records
    partner_id = fields.Many2one(
        'res.partner',
        string='Contact',
        help='Matched or created contact',
    )
    call_id = fields.Many2one(
        'ringcentral.call',
        string='Call',
        help='The callback call made',
    )
    lead_id = fields.Many2one(
        'crm.lead',
        string='Lead/Opportunity',
    )
    
    # Timing
    callback_date = fields.Datetime(string='Callback Date/Time')
    completed_date = fields.Datetime(string='Completed Date')
    
    # Source Tracking
    source_url = fields.Char(string='Source URL')
    utm_source = fields.Char(string='UTM Source')
    utm_campaign = fields.Char(string='UTM Campaign')

    # Basic anti-abuse metadata
    client_ip = fields.Char(string='Client IP', index=True)
    user_agent = fields.Char(string='User Agent')
    
    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'ringcentral.callback.request'
                ) or _('New')
            
            # Try to match existing partner
            if vals.get('visitor_phone') and not vals.get('partner_id'):
                partner = self._find_partner(vals['visitor_phone'], vals.get('visitor_email'))
                if partner:
                    vals['partner_id'] = partner.id
        
        records = super().create(vals_list)
        
        # Notify about new requests
        for record in records:
            record._notify_new_request()
        
        return records

    def _find_partner(self, phone, email=None):
        """Find existing partner by phone or email"""
        domain = []
        
        if phone:
            clean_phone = ''.join(c for c in phone if c.isdigit())[-10:]
            domain = [
                '|', '|',
                ('phone', 'ilike', clean_phone),
                ('mobile', 'ilike', clean_phone),
                ('phone_sanitized', 'ilike', clean_phone),
            ]
        
        if email:
            domain = ['|'] + domain + [('email', '=ilike', email)]
        
        return self.env['res.partner'].search(domain, limit=1) if domain else None

    def _notify_new_request(self):
        """Notify about new callback request"""
        self.ensure_one()
        
        # Get notification channel
        channel = self.env.ref('ringcentral_website.channel_callback_requests', raise_if_not_found=False)
        
        # Notify via bus
        self.env['bus.bus']._sendone(
            'ringcentral_callback_channel',
            'ringcentral_callback',
            {
                'type': 'new_request',
                'id': self.id,
                'name': self.visitor_name,
                'phone': self.visitor_phone,
                'subject': self.subject,
            }
        )

    def action_assign_to_me(self):
        """Assign to current user"""
        self.write({
            'assigned_user_id': self.env.user.id,
            'state': 'assigned',
        })

    def action_start_callback(self):
        """Start the callback call using RingCentral Embeddable widget"""
        self.ensure_one()
        
        if not self.visitor_phone:
            raise UserError(_('No phone number available'))
        
        self.state = 'in_progress'
        
        # Use the RingCentral Embeddable widget for consistent call experience
        return {
            'type': 'ir.actions.client',
            'tag': 'ringcentral_embeddable_call',
            'params': {
                'phone_number': self.visitor_phone,
                'partner_name': self.visitor_name or self.visitor_phone,
                'res_model': 'ringcentral.callback.request',
                'res_id': self.id,
            },
        }

    def action_mark_completed(self):
        """Mark as completed"""
        self.write({
            'state': 'completed',
            'completed_date': fields.Datetime.now(),
        })

    def action_cancel(self):
        """Cancel the request"""
        self.state = 'cancelled'

    def action_create_lead(self):
        """Create CRM lead from request"""
        self.ensure_one()
        
        if self.lead_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'crm.lead',
                'res_id': self.lead_id.id,
                'view_mode': 'form',
            }
        
        lead = self.env['crm.lead'].create({
            'name': f'Callback: {self.subject or self.visitor_name}',
            'contact_name': self.visitor_name,
            'phone': self.visitor_phone,
            'email_from': self.visitor_email,
            'partner_id': self.partner_id.id if self.partner_id else False,
            'description': self.message,
            'type': 'lead',
        })
        
        self.lead_id = lead.id
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'res_id': lead.id,
            'view_mode': 'form',
        }

    def action_create_partner(self):
        """Create partner from request"""
        self.ensure_one()
        
        if self.partner_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'res.partner',
                'res_id': self.partner_id.id,
                'view_mode': 'form',
            }
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Contact'),
            'res_model': 'res.partner',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_name': self.visitor_name,
                'default_phone': self.visitor_phone,
                'default_email': self.visitor_email,
            },
        }
