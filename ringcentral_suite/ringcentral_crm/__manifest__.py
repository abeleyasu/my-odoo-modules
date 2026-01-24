# -*- coding: utf-8 -*-
{
    'name': 'RingCentral CRM Integration',
    'version': '18.0.1.0.0',
    'category': 'Phone',
    'summary': 'Deep CRM integration with RingCentral communications',
    'description': """
RingCentral CRM Integration
===========================
This module provides deep CRM integration:

* Click-to-call from leads/opportunities
* Automatic call logging on leads
* SMS campaigns for leads
* Call activity scheduling
* Lead scoring based on communication
* Communication history on leads
* Auto-assign leads based on call routing

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
        'ringcentral_sms',
        'crm',
    ],
    'data': [
        'views/crm_lead_views.xml',
        'data/crm_activity_data.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
