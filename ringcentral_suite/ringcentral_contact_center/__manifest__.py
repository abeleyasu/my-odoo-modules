# -*- coding: utf-8 -*-
{
    'name': 'RingCentral Contact Center',
    'version': '16.0.1.0.2',
    'category': 'Phone',
    'summary': 'Contact center features - ACD, IVR, queues',
    'description': """
RingCentral Contact Center Module
=================================
This module provides contact center features:

* Call queues management
* Automatic Call Distribution (ACD)
* IVR menu management
* Agent routing
* Queue statistics
* Real-time monitoring

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
        'ringcentral_presence',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/call_queue_views.xml',
        'views/ivr_menu_views.xml',
        'views/ringcentral_menu.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
