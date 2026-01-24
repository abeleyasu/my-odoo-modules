# -*- coding: utf-8 -*-
{
    'name': 'RingCentral HR Integration',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Phone',
    'summary': 'RingCentral integration for HR module',
    'description': """
RingCentral HR Integration
==========================
This module integrates RingCentral with the HR module:

* Click-to-call from employee records
* Call/SMS employees directly
* Track communications with employees
* Schedule meetings with employees
* Employee phone directory sync

    Part of RingCentral Suite by Abel Eyasu - Alkez ERP
    """,
    'author': 'Abel Eyasu',
    'website': 'https://www.alkezz.site',
    'license': 'OPL-1',
    'price': 50,
    'currency': 'USD',
    'depends': [
        'hr',
        'ringcentral_base',
        'ringcentral_call',
        'ringcentral_sms',
    ],
    'data': [
        'views/hr_employee_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
