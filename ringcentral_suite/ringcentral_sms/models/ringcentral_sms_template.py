# -*- coding: utf-8 -*-
"""
RingCentral SMS Template Model
==============================

SMS templates with placeholder support.
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class RingCentralSMSTemplate(models.Model):
    """SMS Template"""
    
    _name = 'ringcentral.sms.template'
    _description = 'SMS Template'
    _order = 'name'
    
    name = fields.Char(
        string='Template Name',
        required=True
    )
    
    body = fields.Text(
        string='Message Body',
        required=True,
        help='Use placeholders like {{partner_name}}, {{company_name}}'
    )
    
    model_id = fields.Many2one(
        'ir.model',
        string='Applies To',
        help='Model this template is designed for'
    )
    
    model = fields.Char(
        string='Model Name',
        related='model_id.model',
        store=True
    )
    
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    
    # Statistics
    use_count = fields.Integer(
        string='Times Used',
        default=0
    )
    
    def render_template(self, record):
        """
        Render template with record data
        
        :param record: Record to get data from
        :return: Rendered message body
        """
        self.ensure_one()
        
        body = self.body
        
        # Common placeholders
        replacements = {
            '{{company_name}}': self.env.company.name or '',
            '{{user_name}}': self.env.user.name or '',
            '{{date}}': fields.Date.today().strftime('%Y-%m-%d'),
        }
        
        # Record-specific placeholders
        if record:
            if hasattr(record, 'name'):
                replacements['{{name}}'] = record.name or ''
            if hasattr(record, 'partner_id') and record.partner_id:
                replacements['{{partner_name}}'] = record.partner_id.name or ''
            elif hasattr(record, 'name'):
                replacements['{{partner_name}}'] = record.name or ''
            if hasattr(record, 'phone'):
                replacements['{{phone}}'] = record.phone or ''
            if hasattr(record, 'email'):
                replacements['{{email}}'] = record.email or ''
        
        for placeholder, value in replacements.items():
            body = body.replace(placeholder, str(value))
        
        # Increment use count
        self.sudo().write({'use_count': self.use_count + 1})
        
        return body
    
    def action_preview(self):
        """Preview template"""
        self.ensure_one()
        
        preview = self.render_template(None)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Template Preview'),
                'message': preview,
                'type': 'info',
                'sticky': True,
            }
        }
