# -*- coding: utf-8 -*-

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Website Widget Settings
    rc_website_widget_enabled = fields.Boolean(
        string='Enable Click-to-Call Widget',
        config_parameter='ringcentral_website.widget_enabled',
        default=True,
    )
    rc_website_show_phone = fields.Boolean(
        string='Show Phone Number',
        config_parameter='ringcentral_website.show_phone',
        default=True,
    )
    rc_website_phone_number = fields.Char(
        string='Display Phone Number',
        config_parameter='ringcentral_website.phone_number',
    )
    rc_website_callback_enabled = fields.Boolean(
        string='Enable Callback Requests',
        config_parameter='ringcentral_website.callback_enabled',
        default=True,
    )
    rc_website_widget_position = fields.Selection([
        ('bottom-right', 'Bottom Right'),
        ('bottom-left', 'Bottom Left'),
        ('top-right', 'Top Right'),
        ('top-left', 'Top Left'),
    ], string='Widget Position',
        config_parameter='ringcentral_website.widget_position',
        default='bottom-right',
    )
    rc_website_widget_color = fields.Char(
        string='Widget Color',
        config_parameter='ringcentral_website.widget_color',
        default='#007bff',
    )
