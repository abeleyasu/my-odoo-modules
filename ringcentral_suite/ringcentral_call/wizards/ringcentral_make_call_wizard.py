# -*- coding: utf-8 -*-
"""
Make Call Wizard
================

Wizard for initiating calls with additional options.
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class RingCentralMakeCallWizard(models.TransientModel):
    """Wizard for making RingCentral calls"""
    
    _name = 'ringcentral.make.call.wizard'
    _description = 'Make Call Wizard'
    
    phone_number = fields.Char(
        string='Phone Number',
        required=True
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Contact'
    )
    
    from_number = fields.Char(
        string='Caller ID',
        help='Leave empty to use default'
    )
    
    play_prompt = fields.Boolean(
        string='Play Connection Prompt',
        default=True
    )
    
    auto_record = fields.Boolean(
        string='Record Call',
        default=False
    )
    
    notes = fields.Text(
        string='Pre-call Notes'
    )
    
    # Related record
    res_model = fields.Char(string='Related Model')
    res_id = fields.Integer(string='Related ID')
    
    @api.model
    def default_get(self, fields_list):
        """Set defaults from context"""
        res = super().default_get(fields_list)
        
        context = self.env.context
        
        if context.get('default_phone_number'):
            res['phone_number'] = context['default_phone_number']
        
        if context.get('default_partner_id'):
            partner = self.env['res.partner'].browse(context['default_partner_id'])
            res['partner_id'] = partner.id
            if not res.get('phone_number'):
                res['phone_number'] = partner.phone or partner.mobile
        
        if context.get('active_model') and context.get('active_id'):
            res['res_model'] = context['active_model']
            res['res_id'] = context['active_id']
            
            # Try to get phone from active record
            if not res.get('phone_number'):
                record = self.env[context['active_model']].browse(context['active_id'])
                if hasattr(record, 'phone'):
                    res['phone_number'] = record.phone
                elif hasattr(record, 'mobile'):
                    res['phone_number'] = record.mobile
                elif hasattr(record, 'partner_id') and record.partner_id:
                    res['phone_number'] = record.partner_id.phone or record.partner_id.mobile
                    res['partner_id'] = record.partner_id.id
        
        # Default caller ID
        user = self.env.user
        company = self.env.company
        res['from_number'] = user.ringcentral_direct_number or company.ringcentral_default_caller_id
        res['auto_record'] = company.ringcentral_auto_record_calls
        res['play_prompt'] = company.ringcentral_call_prompt
        
        return res
    
    def action_call(self):
        """Initiate the call"""
        self.ensure_one()
        
        if not self.phone_number:
            raise UserError(_("Please enter a phone number"))
        
        call_model = self.env['ringcentral.call']
        
        try:
            result = call_model.action_make_call(
                self.phone_number,
                partner_id=self.partner_id.id if self.partner_id else None,
                res_model=self.res_model,
                res_id=self.res_id
            )
            
            # Update call with wizard options
            if result.get('id'):
                call = call_model.browse(result['id'])
                if self.notes:
                    call.write({'notes': self.notes})
                if self.auto_record:
                    call.action_start_recording()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Calling'),
                    'message': _('Calling %s...') % self.phone_number,
                    'type': 'info',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            raise UserError(_("Failed to make call: %s") % str(e))
