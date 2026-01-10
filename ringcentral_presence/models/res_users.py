# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    # Presence relation - search=True makes it searchable without storing
    presence_id = fields.Many2one(
        'ringcentral.presence',
        compute='_compute_presence_id',
        search='_search_presence_id',
        string='Presence',
    )
    presence_status = fields.Selection(
        related='presence_id.presence_status',
        string='Status',
        readonly=True,
    )
    telephony_status = fields.Selection(
        related='presence_id.telephony_status',
        string='Phone',
        readonly=True,
    )

    def _compute_presence_id(self):
        Presence = self.env['ringcentral.presence']
        for user in self:
            user.presence_id = Presence.search([('user_id', '=', user.id)], limit=1)

    def _search_presence_id(self, operator, value):
        """Make presence_id searchable"""
        presences = self.env['ringcentral.presence'].search([('id', operator, value)])
        return [('id', 'in', presences.mapped('user_id').ids)]

    def action_set_presence(self, status=None):
        """Quick action to set presence status"""
        self.ensure_one()
        
        # Get status from parameter or context
        if status is None:
            status = self.env.context.get('default_status', 'available')
        
        Presence = self.env['ringcentral.presence']
        presence = Presence.search([('user_id', '=', self.id)], limit=1)
        
        if not presence:
            presence = Presence.create({
                'user_id': self.id,
                'extension_id': self.rc_extension_id,
            })
        
        if status == 'available':
            presence.action_set_available()
        elif status == 'busy':
            presence.action_set_busy()
        elif status == 'dnd':
            presence.action_set_dnd()
        elif status == 'away':
            presence.action_set_away()
