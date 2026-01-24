# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Call statistics
    call_ids = fields.One2many(
        'ringcentral.call',
        'sale_order_id',
        string='Calls',
    )
    call_count = fields.Integer(
        string='Calls',
        compute='_compute_communication_stats',
    )
    total_call_duration = fields.Float(
        string='Total Call Time (min)',
        compute='_compute_communication_stats',
    )
    
    # SMS statistics  
    sms_ids = fields.One2many(
        'ringcentral.sms',
        'sale_order_id',
        string='SMS Messages',
    )
    sms_count = fields.Integer(
        string='SMS',
        compute='_compute_communication_stats',
    )
    
    # Last communication
    last_communication_date = fields.Datetime(
        string='Last Communication',
        compute='_compute_communication_stats',
    )

    @api.depends('call_ids', 'sms_ids')
    def _compute_communication_stats(self):
        for order in self:
            order.call_count = len(order.call_ids)
            order.total_call_duration = sum(
                c.duration / 60.0 for c in order.call_ids
            )
            order.sms_count = len(order.sms_ids)
            
            # Last communication
            dates = []
            if order.call_ids:
                dates.extend(c.start_time for c in order.call_ids if c.start_time)
            if order.sms_ids:
                dates.extend(s.message_date for s in order.sms_ids if s.message_date)
            
            order.last_communication_date = max(dates) if dates else False

    def action_view_calls(self):
        """View calls related to this order"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Order Calls'),
            'res_model': 'ringcentral.call',
            'view_mode': 'tree,form',
            'domain': [('sale_order_id', '=', self.id)],
            'context': {
                'default_sale_order_id': self.id,
                'default_partner_id': self.partner_id.id,
            },
        }

    def action_view_sms(self):
        """View SMS related to this order"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Order SMS'),
            'res_model': 'ringcentral.sms',
            'view_mode': 'tree,form',
            'domain': [('sale_order_id', '=', self.id)],
            'context': {
                'default_sale_order_id': self.id,
                'default_partner_id': self.partner_id.id,
            },
        }

    def action_quick_call(self):
        """Quick call to customer using RingCentral Embeddable widget"""
        self.ensure_one()
        
        phone = self.partner_id.phone or self.partner_id.mobile
        if not phone:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('No phone number available for this customer'),
                    'type': 'warning',
                }
            }
        
        # Use the RingCentral Embeddable widget for consistent call experience
        return {
            'type': 'ir.actions.client',
            'tag': 'ringcentral_embeddable_call',
            'params': {
                'phone_number': phone,
                'partner_name': self.partner_id.name,
                'res_model': 'sale.order',
                'res_id': self.id,
            },
        }

    def action_send_sms(self):
        """Send SMS to customer"""
        self.ensure_one()
        
        phone = self.partner_id.mobile or self.partner_id.phone
        if not phone:
            return
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Send SMS'),
            'res_model': 'ringcentral.sms.compose',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_phone_number': phone,
                'default_partner_id': self.partner_id.id,
                'default_sale_order_id': self.id,
            },
        }
