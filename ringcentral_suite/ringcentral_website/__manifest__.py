# -*- coding: utf-8 -*-
{
    'name': 'RingCentral Website',
    'version': '16.0.1.0.2',
    'category': 'Phone',
    'summary': 'Click-to-call widget for website visitors',
    'description': """
RingCentral Website Integration
===============================
This module adds website features:

* Click-to-call widget for visitors
* Call request forms
* Live chat to phone escalation
* Callback scheduling
* Real-time agent availability

    Part of RingCentral Suite by Abel Eyasu - Alkez ERP
    """,
    'author': 'Abel Eyasu',
    'website': 'https://www.alkezz.site',
    'license': 'OPL-1',
    'price': 50,
    'currency': 'EUR',
    'depends': [
        'ringcentral_base',
        'ringcentral_call',
        'website',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/website_templates.xml',
        'views/ringcentral_callback_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'ringcentral_website/static/src/js/click_to_call_widget.js',
            'ringcentral_website/static/src/css/click_to_call.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}
