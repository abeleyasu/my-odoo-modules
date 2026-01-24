# -*- coding: utf-8 -*-
{
    'name': 'RingCentral Compliance',
    'version': '18.0.1.0.0',
    'category': 'Phone',
    'summary': 'GDPR, HIPAA, and regulatory compliance for RingCentral',
    'description': """
RingCentral Compliance Module
=============================

⚠️ IMPORTANT: Requires RingCentral Base module ($100) to be installed first.
This module cannot function without the base module.

This module provides compliance features:

* GDPR data subject requests (access, deletion)
* HIPAA compliance tracking
* Consent management
* Data retention automation
* Audit logging
* Compliance reports
* Privacy notices

    Part of RingCentral Suite by Abel Eyasu - Alkez ERP
    """,
    'author': 'Abel Eyasu',
    'website': 'https://www.alkezz.site',
    'license': 'OPL-1',
    'price': 30.00,
    'currency': 'USD',
    'depends': [
        'ringcentral_base',
        'ringcentral_call',
        'ringcentral_sms',
        'ringcentral_recording',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/ringcentral_compliance_security.xml',
        'data/compliance_data.xml',
        'views/compliance_consent_views.xml',
        'views/compliance_request_views.xml',
        'views/ringcentral_menu.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
