# -*- coding: utf-8 -*-
{
    'name': 'RingCentral Project',
    'version': '19.0.1.0.2',
    'category': 'Phone',
    'summary': 'Project and timesheet integration',
    'description': """
RingCentral Project Integration
===============================
This module provides project/timesheet features:

* Auto-create timesheet from calls
* Link calls to tasks
* Project communication stats
* Time tracking from calls

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
        'project',
        'hr_timesheet',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/project_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
