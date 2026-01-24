# -*- coding: utf-8 -*-
{
    'name': 'RingCentral Portal',
    'version': '16.0.1.0.2',
    'category': 'Phone',
    'summary': 'Customer portal for RingCentral communications',
    'description': """
RingCentral Customer Portal
===========================
This module provides customer portal features:

* View call history
* Access voicemail messages
* Download recordings (if permitted)
* View SMS conversation history
* Request callbacks
* Submit communication preferences

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
        'ringcentral_voicemail',
        'ringcentral_recording',
        'portal',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/ringcentral_portal_security.xml',
        'views/portal_templates.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
