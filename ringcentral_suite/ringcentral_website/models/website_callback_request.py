# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class WebsiteCallbackRequest(models.Model):
    _name = 'website.callback.request'
    _description = 'Website Callback Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Name',
        required=True,
    )
    phone = fields.Char(
        string='Phone Number',
        required=True,
    )
    email = fields.Char(string='Email')
    
    # Request Details
    preferred_time = fields.Selection([
        ('asap', 'As Soon As Possible'),
        ('morning', 'Morning (9am - 12pm)'),
        ('afternoon', 'Afternoon (12pm - 5pm)'),
        ('evening', 'Evening (5pm - 8pm)'),
    ], string='Preferred Time', default='asap')
    
    message = fields.Text(string='Message')
    
    # Status
    state = fields.Selection([
        ('new', 'New'),
        ('assigned', 'Assigned'),
        ('calling', 'Calling'),
        ('completed', 'Completed'),
        ('no_answer', 'No Answer'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='new', tracking=True)
    
    # Assignment
    user_id = fields.Many2one(
        'res.users',
        string='Assigned To',
        tracking=True,
    )
    
    # Related Records
    partner_id = fields.Many2one(
        'res.partner',
        string='Contact',
    )
    call_id = fields.Many2one(
        'ringcentral.call',
        string='Call',
    )
    lead_id = fields.Many2one(
        'crm.lead',
        string='Lead',
    )
    
    # Tracking
    source_url = fields.Char(string='Source URL')
    ip_address = fields.Char(string='IP Address')
    user_agent = fields.Char(string='User Agent')
    
    # Timestamps
    callback_time = fields.Datetime(string='Callback Time')
    completed_time = fields.Datetime(string='Completed Time')
    
    # Notes
    notes = fields.Text(string='Notes')

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        
        for record in records:
            # Try to find existing partner
            partner = self.env['res.partner'].search([
                '|',
                ('phone', 'ilike', record.phone[-10:]),
                ('mobile', 'ilike', record.phone[-10:]),
            ], limit=1)
            
            if partner:
                record.partner_id = partner.id
            
            # Notify team
            record._notify_new_request()
        
        return records

    def _notify_new_request(self):
        """Notify team of new callback request"""
        self.ensure_one()
        
        # Send notification
        self.env['bus.bus']._sendone(
            'ringcentral_callback_channel',
            'new_callback_request',
            {
                'id': self.id,
                'name': self.name,
                'phone': self.phone,
                'preferred_time': self.preferred_time,
            }
        )

    def action_assign_to_me(self):
        """Assign callback to current user"""
        self.ensure_one()
        self.write({
            'user_id': self.env.user.id,
            'state': 'assigned',
        })

    def action_call(self):
        """Initiate callback using RingCentral Embeddable widget"""
        self.ensure_one()
        
        self.state = 'calling'
        self.callback_time = fields.Datetime.now()
        
        # Use the RingCentral Embeddable widget for consistent call experience
        return {
            'type': 'ir.actions.client',
            'tag': 'ringcentral_embeddable_call',
            'params': {
                'phone_number': self.phone,
                'partner_name': self.name,
                'res_model': 'website.callback.request',
                'res_id': self.id,
            },
        }

    def action_mark_completed(self):
        """Mark callback as completed"""
        self.ensure_one()
        self.write({
            'state': 'completed',
            'completed_time': fields.Datetime.now(),
        })

    def action_mark_no_answer(self):
        """Mark as no answer"""
        self.ensure_one()
        self.state = 'no_answer'

    def action_cancel(self):
        """Cancel callback request"""
        self.ensure_one()
        self.state = 'cancelled'

    def action_create_lead(self):
        """Create CRM lead from callback request"""
        self.ensure_one()
        
        Lead = self.env.get('crm.lead')
        if not Lead:
            return
        
        lead = Lead.create({
            'name': f'Website Callback: {self.name}',
            'partner_name': self.name,
            'phone': self.phone,
            'email_from': self.email,
            'description': self.message,
            'type': 'lead',
        })
        
        self.lead_id = lead.id
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Lead'),
            'res_model': 'crm.lead',
            'res_id': lead.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_create_partner(self):
        """Create partner from callback request"""
        self.ensure_one()
        
        if self.partner_id:
            return
        
        partner = self.env['res.partner'].create({
            'name': self.name,
            'phone': self.phone,
            'email': self.email,
        })
        
        self.partner_id = partner.id
