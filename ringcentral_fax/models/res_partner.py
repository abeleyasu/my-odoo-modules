# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Fax field (may already exist)
    fax = fields.Char(string='Fax')
    
    # Fax history
    fax_ids = fields.One2many(
        'ringcentral.fax',
        'partner_id',
        string='Faxes',
    )
    fax_count = fields.Integer(
        compute='_compute_fax_count',
        string='Faxes',
    )

    @api.depends('fax_ids')
    def _compute_fax_count(self):
        for partner in self:
            partner.fax_count = len(partner.fax_ids)

    def action_view_faxes(self):
        """View partner's faxes"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Faxes',
            'res_model': 'ringcentral.fax',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }

    def action_send_fax(self):
        """Open send fax wizard"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Send Fax',
            'res_model': 'ringcentral.fax.send',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
                'default_fax_number': self.fax,
            },
        }
