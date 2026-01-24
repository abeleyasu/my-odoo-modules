# -*- coding: utf-8 -*-
{
    'name': 'RingCentral Sale',
    'version': '18.0.1.0.1',
    'category': 'Phone',
    'summary': 'Sales integration and usage billing',
    'description': """
RingCentral Sale Integration
============================
This module provides sales features:

* Link calls to sales orders
* Communication stats on quotations
* Usage-based billing
* Sales team call tracking

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
        'sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
