# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class RingCentralFaxSend(models.TransientModel):
    _name = 'ringcentral.fax.send'
    _description = 'Send Fax Wizard'

    fax_number = fields.Char(
        string='Fax Number',
        required=True,
        help='Enter fax number, e.g., +1234567890',
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Contact',
    )
    
    # Cover Page
    cover_page_id = fields.Many2one(
        'ringcentral.fax.cover.page',
        string='Cover Page Template',
    )
    cover_page_text = fields.Text(
        string='Cover Page Message',
        help='Enter a message for the cover page...',
    )
    
    # Documents
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'ringcentral_fax_send_attachment_rel',
        'wizard_id',
        'attachment_id',
        string='Documents',
        required=True,
    )
    
    # Options
    resolution = fields.Selection([
        ('high', 'High Quality'),
        ('low', 'Standard'),
    ], string='Resolution', default='high')
    
    # Context
    res_model = fields.Char(string='Related Model')
    res_id = fields.Integer(string='Related ID')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')
        
        if active_model and active_id:
            res['res_model'] = active_model
            res['res_id'] = active_id
            
            record = self.env[active_model].browse(active_id)
            
            # Get partner and fax number
            if active_model == 'res.partner':
                res['partner_id'] = active_id
                res['fax_number'] = record.fax
            elif hasattr(record, 'partner_id') and record.partner_id:
                res['partner_id'] = record.partner_id.id
                res['fax_number'] = record.partner_id.fax
        
        return res

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id and self.partner_id.fax:
            self.fax_number = self.partner_id.fax

    @api.onchange('cover_page_id')
    def _onchange_cover_page_id(self):
        if self.cover_page_id:
            self.cover_page_text = self.cover_page_id.greeting

    def action_send(self):
        """Send the fax"""
        self.ensure_one()
        
        if not self.fax_number:
            raise UserError(_('Please provide a fax number'))
        
        if not self.attachment_ids:
            raise UserError(_('Please attach at least one document'))
        
        # Create fax record
        fax_vals = {
            'direction': 'outbound',
            'fax_number': self.fax_number,
            'to_number': self.fax_number,
            'partner_id': self.partner_id.id if self.partner_id else False,
            'attachment_ids': [(6, 0, self.attachment_ids.ids)],
            'cover_page_id': self.cover_page_id.id if self.cover_page_id else False,
            'cover_page_text': self.cover_page_text,
            'resolution': self.resolution,
            'res_model': self.res_model,
            'res_id': self.res_id,
        }
        
        fax = self.env['ringcentral.fax'].create(fax_vals)
        
        # Increment cover page use count
        if self.cover_page_id:
            self.cover_page_id.increment_use_count()
        
        # Send the fax
        fax.action_send_fax()
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ringcentral.fax',
            'res_id': fax.id,
            'view_mode': 'form',
            'target': 'current',
        }
