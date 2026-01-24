# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'RingCentral Multi-Line & Department Configuration',
    'version': '18.0.1.0.0',
    'summary': 'Per-department and per-app phone number configuration for RingCentral',
    'description': """
RingCentral Multi-Line & Department Configuration
==================================================

This module extends the RingCentral integration to support:

* **Multi-Line Support**: Configure multiple phone numbers per company
* **Department Call Queues**: Map Odoo departments to RingCentral call queues
* **Per-App Phone Configuration**: Different caller IDs for CRM, Sales, HR, Support
* **User Extension Mapping**: Link Odoo users to RingCentral extensions
* **Context-Aware Widget**: Automatically select caller ID based on current Odoo app
* **Automatic Sync**: Sync extensions, phone numbers, and call queues from RingCentral

Industry Standards Implemented:
- RingCentral Call Routing API integration
- Call Queue management via API
- Extension-based user mapping
- Context-aware caller ID selection
- Secure phone number authorization

    Part of RingCentral Suite by Abel Eyasu - Alkez ERP
    """,
    'category': 'Productivity/Phone',
    'author': 'Abel Eyasu',
    'website': 'https://www.alkezz.site',
    'license': 'OPL-1',
    'price': 50,
    'currency': 'USD',
    'depends': [
        'ringcentral_base',
        'ringcentral_webrtc',
        'hr',
    ],
    'data': [
        # Security
        'security/ringcentral_multiline_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/cron_data.xml',
        # Views
        'views/ringcentral_extension_views.xml',
        'views/ringcentral_phone_number_views.xml',
        'views/ringcentral_call_queue_views.xml',
        'views/ringcentral_app_config_views.xml',
        'views/res_users_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ringcentral_multiline/static/src/js/context_aware_widget.js',
            'ringcentral_multiline/static/src/xml/context_aware_widget.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
