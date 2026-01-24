# -*- coding: utf-8 -*-
{
    'name': 'RingCentral Presence',
    'version': '18.0.1.0.0',
    'category': 'Phone',
    'summary': 'Real-time user availability and presence management',
    'description': """
RingCentral Presence
====================
This module provides presence/availability features:

* Real-time presence status sync
* Do Not Disturb management
* Availability scheduling
* Presence status in views
* Status change notifications

    Part of RingCentral Suite by Abel Eyasu - Alkez ERP
    """,
    'author': 'Abel Eyasu',
    'website': 'https://www.alkezz.site',
    'license': 'OPL-1',
    'depends': [
        'ringcentral_base',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_users_views.xml',
        'views/ringcentral_presence_views.xml',
        'views/ringcentral_menu.xml',
        'data/presence_cron_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ringcentral_presence/static/src/xml/presence_widget.xml',
            'ringcentral_presence/static/src/js/presence_widget.js',
            'ringcentral_presence/static/src/css/presence.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}
