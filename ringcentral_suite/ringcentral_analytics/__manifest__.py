# -*- coding: utf-8 -*-
{
    'name': 'RingCentral Analytics',
    'version': '18.0.1.0.0',
    'category': 'Phone',
    'summary': 'Analytics and reporting for RingCentral communications',
    'description': """
RingCentral Analytics
=====================
This module provides analytics and reporting:

* Call volume dashboards
* Agent performance metrics
* Call duration analytics
* SMS statistics
* Response time tracking
* Trend analysis
* Custom reports

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
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/ringcentral_analytics_views.xml',
        'reports/call_report_views.xml',
        'views/ringcentral_menu.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
