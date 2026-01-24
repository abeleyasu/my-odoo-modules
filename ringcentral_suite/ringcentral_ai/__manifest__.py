# -*- coding: utf-8 -*-
{
    'name': 'RingCentral AI',
    'version': '18.0.1.0.0',
    'category': 'Phone',
    'summary': 'AI transcription and sentiment analysis',
    'description': """
RingCentral AI Module
=====================
This module provides AI-powered features:

* Automatic call transcription
* Sentiment analysis
* Conversation intelligence
* Key topics extraction
* Action items detection
* Call summaries

    Part of RingCentral Suite by Abel Eyasu - Alkez ERP
    """,
    'author': 'Abel Eyasu',
    'website': 'https://www.alkezz.site',
    'license': 'OPL-1',
    'depends': [
        'ringcentral_base',
        'ringcentral_call',
        'ringcentral_recording',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ai_data.xml',
        'views/ai_transcript_views.xml',
        'views/ringcentral_menu.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
