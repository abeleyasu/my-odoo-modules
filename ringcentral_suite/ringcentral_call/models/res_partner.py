# -*- coding: utf-8 -*-
"""
Partner Extension for RingCentral
=================================

Add call history and quick actions to partners.
"""

from odoo import api, fields, models


class ResPartner(models.Model):
    """Partner extension for RingCentral call history"""
    
    _inherit = 'res.partner'
    
    # ===========================
    # Call History
    # ===========================
    
    ringcentral_call_ids = fields.One2many(
        'ringcentral.call',
        'partner_id',
        string='Call History'
    )
    
    ringcentral_call_count = fields.Integer(
        string='Calls',
        compute='_compute_call_count'
    )
    
    ringcentral_last_call_date = fields.Datetime(
        string='Last Call',
        compute='_compute_last_call_date'
    )
    
    ringcentral_total_call_duration = fields.Integer(
        string='Total Call Duration',
        compute='_compute_call_stats'
    )
    
    # ===========================
    # Computed Fields
    # ===========================
    
    @api.depends('ringcentral_call_ids')
    def _compute_call_count(self):
        for partner in self:
            partner.ringcentral_call_count = len(partner.ringcentral_call_ids)
    
    @api.depends('ringcentral_call_ids.start_time')
    def _compute_last_call_date(self):
        for partner in self:
            calls = partner.ringcentral_call_ids.sorted('start_time', reverse=True)
            partner.ringcentral_last_call_date = calls[0].start_time if calls else False
    
    @api.depends('ringcentral_call_ids.duration')
    def _compute_call_stats(self):
        for partner in self:
            partner.ringcentral_total_call_duration = sum(
                partner.ringcentral_call_ids.mapped('duration')
            )
    
    # ===========================
    # Actions
    # ===========================
    
    def action_ringcentral_call(self):
        """Quick action to call partner - opens call control widget"""
        self.ensure_one()
        
        phone_number = self.phone or self.mobile
        if not phone_number:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Phone Number'),
                    'message': _('This contact has no phone number.'),
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
                    'phone_number': phone_number,
                    'partner_name': self.name,
                    'res_model': 'res.partner',
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
    
    def action_view_calls(self):
        """Open call history for partner"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Calls - {self.name}',
            'res_model': 'ringcentral.call',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {
                'default_partner_id': self.id,
                'default_phone_number': self.phone or self.mobile,
            },
        }
    
    def action_send_sms(self):
        """Quick action to send SMS to partner"""
        self.ensure_one()
        
        phone_number = self.mobile or self.phone
        if not phone_number:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No Phone Number',
                    'message': 'This contact has no phone number.',
                    'type': 'warning',
                }
            }
        
        # Open SMS compose wizard
        return {
            'type': 'ir.actions.act_window',
            'name': 'Send SMS',
            'res_model': 'ringcentral.sms.compose',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
                'default_phone_number': phone_number,
            },
        }
