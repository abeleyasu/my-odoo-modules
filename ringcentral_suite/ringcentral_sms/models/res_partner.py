# -*- coding: utf-8 -*-
"""
Partner Extension for SMS
=========================

Add SMS functionality to partners.
"""

from odoo import api, fields, models


class ResPartner(models.Model):
    """Partner extension for SMS"""
    
    _inherit = 'res.partner'
    
    ringcentral_sms_ids = fields.One2many(
        'ringcentral.sms',
        'partner_id',
        string='SMS Messages'
    )
    
    ringcentral_sms_count = fields.Integer(
        string='SMS Count',
        compute='_compute_sms_count'
    )
    
    @api.depends('ringcentral_sms_ids')
    def _compute_sms_count(self):
        for partner in self:
            partner.ringcentral_sms_count = len(partner.ringcentral_sms_ids)
    
    def action_view_sms(self):
        """View SMS history for partner"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'SMS - {self.name}',
            'res_model': 'ringcentral.sms',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {
                'default_partner_id': self.id,
                'default_phone_number': self.mobile or self.phone,
            },
        }
