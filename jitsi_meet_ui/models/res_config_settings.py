# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    jitsi_server_url = fields.Char(
        string='Jitsi Server URL',
        config_parameter='jitsi.server_url',
        help='Custom Jitsi server URL. Leave blank to use meet.jit.si'
    )
    jitsi_jwt_app_id = fields.Char(
        string='JWT App ID',
        config_parameter='jitsi.jwt.app_id',
        help='Application ID for JWT token authentication'
    )
    jitsi_jwt_app_secret = fields.Char(
        string='JWT App Secret',
        config_parameter='jitsi.jwt.app_secret',
        help='Secret key for JWT token signing'
    )
    jitsi_server_domain = fields.Char(
        string='Jitsi Server Domain',
        config_parameter='jitsi.server_domain',
        default='meet.jit.si',
        help='Domain name for JWT token (usually your Jitsi server domain)'
    )
