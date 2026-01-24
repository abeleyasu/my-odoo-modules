# -*- coding: utf-8 -*-
{
    'name': 'RingCentral Call',
    'version': '18.0.1.0.2',
    'category': 'Phone',
    'summary': 'RingCentral Voice Calling - Click-to-Dial, Call Logging, Call Control',
    'description': '''
RingCentral Call Integration for Odoo 18
========================================

Voice calling features:
- Click-to-dial from any phone field
- RingOut two-legged calling
- Call Control (hold, mute, transfer)
- Call logging with CDR sync
- Incoming call popup with caller ID
- Call history on partners and leads
- Integration with Odoo activities

Extends base_phone module for native click-to-dial functionality.

    Part of RingCentral Suite by Abel Eyasu - Alkez ERP
    ''',
    'author': 'Abel Eyasu',
    'website': 'https://www.alkezz.site',
    'license': 'OPL-1',
    'price': 50,
    'currency': 'EUR',
    'depends': [
        'ringcentral_base',
        'mail',
        'contacts',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_activity_type_data.xml',
        'views/ringcentral_call_views.xml',
        'views/res_partner_views.xml',
        'views/ringcentral_menu.xml',
        'wizards/ringcentral_make_call_wizard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ringcentral_call/static/src/components/**/*.js',
            'ringcentral_call/static/src/components/**/*.xml',
            'ringcentral_call/static/src/components/**/*.scss',
            'ringcentral_call/static/src/actions/**/*.js',
        ],
    },
    'images': [
        'static/description/banner.svg',
        'static/description/icon.png',
    ],
    'installable': True,
    'auto_install': False,
}
