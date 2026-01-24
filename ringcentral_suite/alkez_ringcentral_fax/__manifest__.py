# -*- coding: utf-8 -*-
{
    'name': 'RingCentral Fax',
    'version': '19.0.1.0.2',
    'category': 'Phone',
    'summary': 'Send and receive faxes via RingCentral',
    'description': """
RingCentral Fax Integration
===========================
This module provides fax integration:

* Send faxes from Odoo
* Receive incoming faxes
* Fax from documents/attachments
* Fax status tracking
* Fax cover pages
* Contact fax history

    Part of RingCentral Suite by Abel Eyasu - Alkez ERP
    """,
    'author': 'Abel Eyasu',
    'website': 'https://www.alkezz.site',
    'license': 'OPL-1',
    'price': 50,
    'currency': 'EUR',
    'depends': [
        'ringcentral_base',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/fax_cover_page_data.xml',
        'views/ringcentral_fax_views.xml',
        'views/ringcentral_menu.xml',
        'wizards/ringcentral_fax_send_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
