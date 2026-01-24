# -*- coding: utf-8 -*-
{
    'name': 'RingCentral SMS',
    'version': '18.0.1.1.0',
    'category': 'Phone',
    'summary': 'RingCentral SMS/MMS Messaging Integration',
    'description': '''
RingCentral SMS Integration for Odoo 18
=======================================

SMS/MMS messaging features:
- Send SMS from any phone field
- Send SMS from Chatter
- Receive SMS via webhook
- SMS conversation threads
- MMS with attachments (multipart upload)
- SMS templates
- Delivery tracking
- Batch SMS sending
- Retry queue for failed messages

Integrates with contacts, CRM, and other Odoo apps.

    Part of RingCentral Suite by Abel Eyasu - Alkez ERP
    ''',
    'author': 'Abel Eyasu',
    'website': 'https://www.alkezz.site',
    'license': 'OPL-1',
    'depends': [
        'ringcentral_base',
        'mail',
        'contacts',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/sms_template_data.xml',
        'data/ir_cron_data.xml',
        'views/ringcentral_sms_views.xml',
        'views/ringcentral_menu.xml',
        'wizards/ringcentral_sms_compose_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
