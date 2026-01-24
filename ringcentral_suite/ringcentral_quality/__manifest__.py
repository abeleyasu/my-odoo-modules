# -*- coding: utf-8 -*-
{
    'name': 'RingCentral Quality',
    'version': '18.0.1.0.1',
    'category': 'Phone',
    'summary': 'Call quality monitoring and metrics',
    'description': """
RingCentral Quality Module
==========================
This module provides call quality features:

* Real-time quality metrics (MOS, jitter, latency)
* Quality alerts and notifications
* Quality trend analysis
* Network diagnostics
* Quality reports

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
        'data/quality_data.xml',
        'views/call_quality_views.xml',
        'views/ringcentral_menu.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
