# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)

def post_init_hook(env):
    # placeholder: could create demo data or config parameters
    # Odoo calls post_init_hook with the registry/env in newer versions
    _logger.info('jitsi_meet_ui: post_init_hook executed')

def uninstall_hook(env):
    # cleanup any module-specific records if desired
    # Expecting an Environment or registry; normalize to env
    try:
        if hasattr(env, 'registry') and not hasattr(env, 'cursor'):
            # env is likely a registry object; create an Environment
            cr = env.cursor()
            env = api.Environment(cr, SUPERUSER_ID, {})
    except Exception:
        # fallback: try to use env as-is
        pass
    try:
        meetings = env['jitsi.meeting'].search([])
        if meetings:
            count = len(meetings)
            meetings.unlink()
            _logger.info('jitsi_meet_ui: removed %d meetings on uninstall', count)
    except Exception:
        _logger.exception('jitsi_meet_ui: error during uninstall cleanup')
