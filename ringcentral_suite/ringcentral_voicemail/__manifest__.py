# -*- coding: utf-8 -*-
{
    'name': 'RingCentral Voicemail',
    'version': '18.0.1.0.0',
    'category': 'Phone',
    'summary': 'Visual voicemail with transcription',
    'description': """
RingCentral Voicemail
====================
This module provides visual voicemail features:

* Visual voicemail inbox
* Voicemail transcription
* Voicemail to email
* Quick callback from voicemail
* Voicemail greeting management
* Multi-user voicemail boxes

    Part of RingCentral Suite by Abel Eyasu - Alkez ERP
    """,
    'author': 'Abel Eyasu',
    'website': 'https://www.alkezz.site',
    'license': 'OPL-1',
    'price': 50,
    'currency': 'USD',
    'depends': [
        'ringcentral_base',
        'ringcentral_call',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/ringcentral_voicemail_views.xml',
        'views/ringcentral_menu.xml',
        'data/voicemail_cron_data.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
