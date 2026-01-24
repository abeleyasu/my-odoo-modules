# -*- coding: utf-8 -*-
{
    'name': 'RingCentral Base',
    'version': '18.0.1.1.0',
    'category': 'Phone',
    'summary': 'RingCentral Integration Base Module - Core SDK and Authentication',
    'description': '''
RingCentral Base Integration for Odoo 18
========================================

⚠️ IMPORTANT: This is the REQUIRED base module for all RingCentral integrations.
Install this module FIRST before installing any other RingCentral modules.

Core module providing:
- RingCentral API SDK wrapper with token caching
- JWT and OAuth 2.0 authentication
- Encrypted credential storage
- Secure webhook handling with signature verification
- Configuration settings with production mode
- API health monitoring
- Error handling and retry logic
- Webhook event logging and retry queue
- Multi-company support

This is the foundation module for all RingCentral integrations.

    Part of RingCentral Suite by Abel Eyasu - Alkez ERP
    ''',
    'author': 'Abel Eyasu',
    'website': 'https://www.alkezz.site',
    'license': 'OPL-1',
    'price': 100.00,
    'currency': 'USD',
    'depends': [
        'base',
        'mail',
    ],
    'external_dependencies': {
        'python': ['ringcentral', 'requests', 'cryptography', 'requests_toolbelt'],
    },
    'data': [
        'security/ringcentral_security.xml',
        'security/ir.model.access.csv',
        'security/ringcentral_record_rules.xml',
        'data/ir_cron_data.xml',
        'data/ir_config_parameter_data.xml',
        'views/res_config_settings_views.xml',
        'views/ringcentral_api_log_views.xml',
        'views/ringcentral_menu.xml',
        'views/ringcentral_webhook_log_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ringcentral_base/static/src/services/ringcentral_service.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
