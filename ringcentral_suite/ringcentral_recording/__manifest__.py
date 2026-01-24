# -*- coding: utf-8 -*-
{
    'name': 'RingCentral Recording',
    'version': '16.0.1.0.2',
    'category': 'Phone',
    'summary': 'Call recording management and compliance',
    'description': """
RingCentral Call Recording
==========================
This module provides call recording integration:

* Automatic and on-demand call recording
* Recording playback and download
* Recording storage management
* Transcription integration
* Compliance and retention policies
* Recording consent management
* Search recordings by call, partner, date

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
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/recording_retention_data.xml',
        'views/ringcentral_recording_views.xml',
        'views/ringcentral_menu.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
