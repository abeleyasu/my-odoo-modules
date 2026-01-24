# -*- coding: utf-8 -*-
# Copyright 2025-2026 Abel Eyasu - Alkez ERP
# License OPL-1 (Odoo Proprietary License v1.0)

def post_init_hook(env):
    """
    Post-initialization hook for RingCentral Suite.
    Runs after module installation to configure defaults.
    """
    # Set default configuration if not already set
    IrConfigParameter = env['ir.config_parameter'].sudo()
    
    # Ensure webhook security is enabled by default
    if not IrConfigParameter.get_param('ringcentral.webhook_verify_signature'):
        IrConfigParameter.set_param('ringcentral.webhook_verify_signature', 'True')
    
    if not IrConfigParameter.get_param('ringcentral.webhook_ip_check'):
        IrConfigParameter.set_param('ringcentral.webhook_ip_check', 'True')
    
    # Log installation
    env['ir.logging'].sudo().create({
        'name': 'RingCentral Suite',
        'type': 'server',
        'level': 'info',
        'message': 'RingCentral Suite installed successfully. Configure at Settings > RingCentral.',
        'path': 'ringcentral_suite',
        'line': '0',
        'func': 'post_init_hook',
    })
