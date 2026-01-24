# -*- coding: utf-8 -*-
{
    'name': 'RingCentral Video Meetings',
    'version': '19.0.1.0.2',
    'category': 'Phone',
    'summary': 'Video meetings integration with RingCentral',
    'description': """
RingCentral Video Meetings
=========================
This module provides video meeting integration:

* Create RingCentral Video meetings from Odoo
* Calendar event integration
* Meeting links in invitations
* Meeting recording support
* Join meeting from Odoo
* Meeting analytics and reports

    Part of RingCentral Suite by Abel Eyasu - Alkez ERP
    """,
    'author': 'Abel Eyasu',
    'website': 'https://www.alkezz.site',
    'license': 'OPL-1',
    'price': 50,
    'currency': 'EUR',
    'depends': [
        'ringcentral_base',
        'calendar',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/ringcentral_meeting_views.xml',
        'views/calendar_event_views.xml',
        'views/ringcentral_menu.xml',
        'wizards/ringcentral_meeting_wizard_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
