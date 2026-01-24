# -*- coding: utf-8 -*-
"""
SMS Compose Wizard
==================

Wizard for composing and sending SMS messages.
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class RingCentralSMSCompose(models.TransientModel):
    """SMS Compose Wizard"""
    
    _name = 'ringcentral.sms.compose'
    _description = 'Compose SMS'
    
    phone_number = fields.Char(
        string='Phone Number',
        required=True
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Contact'
    )
    
    body = fields.Text(
        string='Message',
        required=True
    )
    
    char_count = fields.Integer(
        string='Characters',
        compute='_compute_char_count'
    )
    
    sms_count = fields.Integer(
        string='SMS Parts',
        compute='_compute_char_count'
    )
    
    template_id = fields.Many2one(
        'ringcentral.sms.template',
        string='Template'
    )
    
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'ringcentral_sms_compose_attachment_rel',
        'wizard_id',
        'attachment_id',
        string='Attachments'
    )
    
    # Related record
    res_model = fields.Char(string='Related Model')
    res_id = fields.Integer(string='Related ID')
    
    @api.depends('body')
    def _compute_char_count(self):
        for wizard in self:
            body = wizard.body or ''
            wizard.char_count = len(body)
            # Standard SMS is 160 chars, concatenated SMS is 153 per part
            if len(body) <= 160:
                wizard.sms_count = 1
            else:
                wizard.sms_count = (len(body) + 152) // 153
    
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
                res['phone_number'] = partner.mobile or partner.phone
        
        if context.get('active_model') and context.get('active_id'):
            res['res_model'] = context['active_model']
            res['res_id'] = context['active_id']
            
            # Try to get phone from active record
            if not res.get('phone_number'):
                record = self.env[context['active_model']].browse(context['active_id'])
                if hasattr(record, 'mobile'):
                    res['phone_number'] = record.mobile
                elif hasattr(record, 'phone'):
                    res['phone_number'] = record.phone
                elif hasattr(record, 'partner_id') and record.partner_id:
                    res['phone_number'] = record.partner_id.mobile or record.partner_id.phone
                    res['partner_id'] = record.partner_id.id
        
        return res
    
    @api.onchange('template_id')
    def _onchange_template_id(self):
        """Apply template to body"""
        if self.template_id:
            record = None
            if self.res_model and self.res_id:
                record = self.env[self.res_model].browse(self.res_id)
            elif self.partner_id:
                record = self.partner_id
            
            self.body = self.template_id.render_template(record)
    
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Update phone number from partner"""
        if self.partner_id and not self.phone_number:
            self.phone_number = self.partner_id.mobile or self.partner_id.phone
    
    def action_send(self):
        """Send SMS"""
        self.ensure_one()
        
        if not self.phone_number:
            raise UserError(_("Please enter a phone number"))
        
        if not self.body:
            raise UserError(_("Please enter a message"))
        
        sms_model = self.env['ringcentral.sms']
        
        try:
            result = sms_model.action_send_sms(
                phone_number=self.phone_number,
                message=self.body,
                partner_id=self.partner_id.id if self.partner_id else None,
                res_model=self.res_model,
                res_id=self.res_id,
                attachments=self.attachment_ids.ids if self.attachment_ids else None
            )
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('SMS Sent'),
                    'message': _('Message sent to %s') % self.phone_number,
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            raise UserError(_("Failed to send SMS: %s") % str(e))
    
    def action_send_and_new(self):
        """Send SMS and open new compose wizard"""
        self.action_send()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Send SMS'),
            'res_model': 'ringcentral.sms.compose',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_res_model': self.res_model,
                'default_res_id': self.res_id,
            },
        }
