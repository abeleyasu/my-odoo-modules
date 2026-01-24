# -*- coding: utf-8 -*-
{
    'name': 'RingCentral WebRTC',
    'version': '17.0.1.0.2',
    'category': 'Phone',
    'summary': 'Browser-based softphone using WebRTC',
    'description': """
RingCentral WebRTC Softphone
============================
This module provides a browser-based softphone:

* Embedded softphone in Odoo
* Click-to-dial from browser
* Receive calls in browser
* Call controls (hold, mute, transfer)
* Audio device selection
* WebRTC-based audio (SIP.js)

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
        'web',
    ],
    'data': [
        'views/webrtc_views.xml',
        'views/res_users_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # RingCentral Embeddable widget (official RingCentral phone)
            'ringcentral_webrtc/static/src/js/ringcentral_embeddable.js',
            'ringcentral_webrtc/static/src/js/ringcentral_call_action.js',
            'ringcentral_webrtc/static/src/js/click_to_call_widget.js',
            'ringcentral_webrtc/static/src/xml/embeddable_templates.xml',
            'ringcentral_webrtc/static/src/xml/click_to_call_templates.xml',
            'ringcentral_webrtc/static/src/css/embeddable.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}
