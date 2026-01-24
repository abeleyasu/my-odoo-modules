# -*- coding: utf-8 -*-
"""
RingCentral Helpdesk Integration
================================

Provides communication integration for helpdesk tickets.
Compatible with both OCA helpdesk_mgmt and Odoo Enterprise helpdesk.
"""

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    # Communication Statistics
    call_count = fields.Integer(
        compute='_compute_communication_stats',
        string='Calls',
    )
    sms_count = fields.Integer(
        compute='_compute_communication_stats',
        string='SMS',
    )
    
    # Last Communication
    last_call_date = fields.Datetime(
        compute='_compute_last_communication',
        string='Last Call',
    )
    
    # Direct Relations
    ringcentral_call_ids = fields.Many2many(
        'ringcentral.call',
        'helpdesk_ticket_call_rel',
        'ticket_id',
        'call_id',
        string='Related Calls',
    )
    ringcentral_sms_ids = fields.Many2many(
        'ringcentral.sms',
        'helpdesk_ticket_sms_rel',
        'ticket_id',
        'sms_id',
        string='Related SMS',
    )

    def _compute_communication_stats(self):
        for ticket in self:
            ticket.call_count = len(ticket.ringcentral_call_ids)
            ticket.sms_count = len(ticket.ringcentral_sms_ids)

    def _compute_last_communication(self):
        for ticket in self:
            calls = ticket.ringcentral_call_ids.sorted('create_date', reverse=True)
            ticket.last_call_date = calls[0].create_date if calls else False

    def _get_ticket_phone(self):
        """
        Get phone number for ticket, compatible with multiple helpdesk modules.
        
        Supports:
        - OCA helpdesk_mgmt: uses partner_id.phone/mobile
        - Odoo Enterprise: uses partner_phone field
        """
        self.ensure_one()
        
        # Try partner_phone field first (Enterprise)
        if hasattr(self, 'partner_phone') and self.partner_phone:
            return self.partner_phone
        
        # Try partner_mobile field (some versions)
        if hasattr(self, 'partner_mobile') and self.partner_mobile:
            return self.partner_mobile
        
        # Fall back to partner's phone/mobile (OCA)
        if self.partner_id:
            return self.partner_id.phone or self.partner_id.mobile
        
        return False

    def action_call(self):
        """Quick call action - shows call control widget"""
        self.ensure_one()
        
        phone = self._get_ticket_phone()
        
        if not phone:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('No phone number available'),
                    'type': 'warning',
                }
            }
        
        call_model = self.env['ringcentral.call']
        
        try:
            # Return client action to use RingCentral Embeddable widget
            return {
                'type': 'ir.actions.client',
                'tag': 'ringcentral_embeddable_call',
                'params': {
                    'phone_number': phone,
                    'partner_name': self.partner_id.name if self.partner_id else self.name,
                    'res_model': 'helpdesk.ticket',
                    'res_id': self.id,
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Call Failed'),
                    'message': str(e),
                    'type': 'danger',
                }
            }

    def action_send_sms(self):
        """Quick SMS action"""
        self.ensure_one()
        
        phone = self._get_ticket_phone()
        
        if not phone:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('No phone number available'),
                    'type': 'warning',
                }
            }
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Send SMS'),
            'res_model': 'ringcentral.sms.compose',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_phone_number': phone,
                'default_partner_id': self.partner_id.id if self.partner_id else False,
                'default_res_model': 'helpdesk.ticket',
                'default_res_id': self.id,
            },
        }

    def action_view_calls(self):
        """View all calls for this ticket"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Calls'),
            'res_model': 'ringcentral.call',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.ringcentral_call_ids.ids)],
        }

    def action_view_sms(self):
        """View all SMS for this ticket"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('SMS Messages'),
            'res_model': 'ringcentral.sms',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.ringcentral_sms_ids.ids)],
        }

    def link_call(self, call_id):
        """Link a call to this ticket"""
        self.ensure_one()
        self.ringcentral_call_ids = [(4, call_id)]

    def link_sms(self, sms_id):
        """Link an SMS to this ticket"""
        self.ensure_one()
        self.ringcentral_sms_ids = [(4, sms_id)]

    @api.model
    def create_from_call(self, call_data, team_id=None):
        """
        Create ticket from incoming call.
        
        Compatible with both OCA helpdesk_mgmt and Odoo Enterprise helpdesk.
        """
        partner_id = call_data.get('partner_id')
        phone = call_data.get('phone_number')
        
        # Get default team
        if not team_id:
            team = self.env['helpdesk.team'].search([], limit=1)
            team_id = team.id if team else False
        
        ticket_vals = {
            'name': f'Phone Inquiry: {phone}',
            'partner_id': partner_id,
            'team_id': team_id,
            'description': f'Ticket created from incoming call on {fields.Datetime.now()}',
        }
        
        # Add partner_phone field if it exists on the model (Enterprise)
        if 'partner_phone' in self._fields:
            ticket_vals['partner_phone'] = phone
        
        ticket = self.create(ticket_vals)
        
        # Link the call if provided
        if call_data.get('call_id'):
            ticket.link_call(call_data['call_id'])
        
        return ticket
