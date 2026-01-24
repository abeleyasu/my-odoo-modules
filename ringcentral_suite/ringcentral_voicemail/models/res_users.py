# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    # Voicemail settings
    rc_voicemail_enabled = fields.Boolean(
        string='Voicemail Enabled',
        default=True,
    )
    rc_voicemail_email_notification = fields.Boolean(
        string='Email Notification',
        default=True,
        help='Send email notification for new voicemails',
    )
    rc_voicemail_count = fields.Integer(
        compute='_compute_voicemail_count',
        string='Unread Voicemails',
    )

    def _compute_voicemail_count(self):
        Voicemail = self.env['ringcentral.voicemail']
        for user in self:
            user.rc_voicemail_count = Voicemail.search_count([
                ('user_id', '=', user.id),
                ('state', '=', 'new'),
            ])

    def action_view_voicemails(self):
        """View user's voicemails"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'My Voicemails',
            'res_model': 'ringcentral.voicemail',
            'view_mode': 'tree,form',
            'domain': [('user_id', '=', self.id)],
            'context': {'search_default_filter_new': 1},
        }


class ResCompany(models.Model):
    _inherit = 'res.company'

    rc_auto_download_voicemail = fields.Boolean(
        string='Auto Download Voicemail',
        default=True,
    )
    rc_auto_transcribe_voicemail = fields.Boolean(
        string='Auto Transcribe Voicemail',
        default=False,
    )
