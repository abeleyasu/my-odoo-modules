# -*- coding: utf-8 -*-
{
    'name': 'RingCentral Helpdesk Integration',
    'version': '18.0.1.0.2',
    'category': 'Phone',
    'summary': 'Helpdesk ticket integration with RingCentral',
    'description': """
RingCentral Helpdesk Integration
================================
This module integrates RingCentral with Helpdesk:

* Click-to-call from tickets
* Auto-create tickets from calls
* Call logging on tickets
* SMS communication on tickets
* Communication history tracking

    Part of RingCentral Suite by Abel Eyasu - Alkez ERP
    """,
    'author': 'Abel Eyasu',
    'website': 'https://www.alkezz.site',
    'license': 'LGPL-3',
    'price': 50,
    'currency': 'EUR',
    'depends': [
        'ringcentral_base',
        'ringcentral_call',
        'ringcentral_sms',
        'helpdesk_mgmt',
    ],
    'data': [
        'views/helpdesk_ticket_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
