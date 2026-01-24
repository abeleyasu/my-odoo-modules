# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError
import logging

_logger = logging.getLogger(__name__)


class RingCentralPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        
        if partner.ringcentral_portal_access:
            if 'call_count' in counters and partner.ringcentral_can_view_calls:
                values['call_count'] = partner._get_portal_call_count()
            if 'sms_count' in counters and partner.ringcentral_can_view_sms:
                values['sms_count'] = partner._get_portal_sms_count()
            if 'voicemail_count' in counters and partner.ringcentral_can_view_voicemail:
                values['voicemail_count'] = partner._get_portal_voicemail_count()
            if 'recording_count' in counters and partner.ringcentral_can_view_recordings:
                values['recording_count'] = partner._get_portal_recording_count()
        
        return values

    @http.route(['/my/calls', '/my/calls/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_calls(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        partner = request.env.user.partner_id
        
        if not partner.ringcentral_portal_access or not partner.ringcentral_can_view_calls:
            raise AccessError(_('You do not have access to call history.'))
        
        Call = request.env['ringcentral.call']
        
        domain = [('partner_id', '=', partner.id)]
        
        if date_begin and date_end:
            domain += [
                ('start_time', '>=', date_begin),
                ('start_time', '<=', date_end),
            ]
        
        searchbar_sortings = {
            'date': {'label': _('Date'), 'order': 'start_time desc'},
            'duration': {'label': _('Duration'), 'order': 'duration desc'},
        }
        
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']
        
        call_count = Call.search_count(domain)
        pager = portal_pager(
            url='/my/calls',
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=call_count,
            page=page,
            step=20,
        )
        
        calls = Call.search(domain, order=order, limit=20, offset=pager['offset'])
        
        values = {
            'calls': calls,
            'page_name': 'calls',
            'pager': pager,
            'default_url': '/my/calls',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        }
        
        return request.render('ringcentral_portal.portal_my_calls', values)

    @http.route(['/my/sms', '/my/sms/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_sms(self, page=1, sortby=None, **kw):
        partner = request.env.user.partner_id
        
        if not partner.ringcentral_portal_access or not partner.ringcentral_can_view_sms:
            raise AccessError(_('You do not have access to SMS history.'))
        
        SMS = request.env['ringcentral.sms']
        
        domain = [('partner_id', '=', partner.id)]
        
        searchbar_sortings = {
            'date': {'label': _('Date'), 'order': 'message_date desc'},
        }
        
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']
        
        sms_count = SMS.search_count(domain)
        pager = portal_pager(
            url='/my/sms',
            url_args={'sortby': sortby},
            total=sms_count,
            page=page,
            step=20,
        )
        
        messages = SMS.search(domain, order=order, limit=20, offset=pager['offset'])
        
        values = {
            'messages': messages,
            'page_name': 'sms',
            'pager': pager,
            'default_url': '/my/sms',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        }
        
        return request.render('ringcentral_portal.portal_my_sms', values)

    @http.route(['/my/voicemails', '/my/voicemails/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_voicemails(self, page=1, sortby=None, **kw):
        partner = request.env.user.partner_id
        
        if not partner.ringcentral_portal_access or not partner.ringcentral_can_view_voicemail:
            raise AccessError(_('You do not have access to voicemail history.'))
        
        Voicemail = request.env['ringcentral.voicemail']
        
        domain = [('partner_id', '=', partner.id)]
        
        searchbar_sortings = {
            'date': {'label': _('Date'), 'order': 'received_date desc'},
        }
        
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']
        
        vm_count = Voicemail.search_count(domain)
        pager = portal_pager(
            url='/my/voicemails',
            url_args={'sortby': sortby},
            total=vm_count,
            page=page,
            step=20,
        )
        
        voicemails = Voicemail.search(domain, order=order, limit=20, offset=pager['offset'])
        
        values = {
            'voicemails': voicemails,
            'page_name': 'voicemails',
            'pager': pager,
            'default_url': '/my/voicemails',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        }
        
        return request.render('ringcentral_portal.portal_my_voicemails', values)

    @http.route(['/my/recordings', '/my/recordings/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_recordings(self, page=1, sortby=None, **kw):
        partner = request.env.user.partner_id

        if not partner.ringcentral_portal_access or not partner.ringcentral_can_view_recordings:
            raise AccessError(_('You do not have access to recordings.'))

        Recording = request.env['ringcentral.recording']
        domain = [('partner_id', '=', partner.id)]

        searchbar_sortings = {
            'date': {'label': _('Date'), 'order': 'recording_date desc'},
            'duration': {'label': _('Duration'), 'order': 'duration desc'},
        }

        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        recording_count = Recording.search_count(domain)
        pager = portal_pager(
            url='/my/recordings',
            url_args={'sortby': sortby},
            total=recording_count,
            page=page,
            step=20,
        )

        recordings = Recording.search(domain, order=order, limit=20, offset=pager['offset'])

        values = {
            'recordings': recordings,
            'page_name': 'recordings',
            'pager': pager,
            'default_url': '/my/recordings',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        }

        return request.render('ringcentral_portal.portal_my_recordings', values)

    @http.route('/my/communication-preferences', type='http', auth='user', website=True)
    def portal_communication_preferences(self, **kw):
        partner = request.env.user.partner_id
        
        if not partner.ringcentral_portal_access:
            raise AccessError(_('You do not have access to communication preferences.'))
        
        values = {
            'partner': partner,
            'page_name': 'preferences',
        }
        
        return request.render('ringcentral_portal.portal_communication_preferences', values)

    @http.route('/my/communication-preferences/save', type='http', auth='user', website=True, methods=['POST'])
    def portal_save_preferences(self, **post):
        partner = request.env.user.partner_id
        
        if not partner.ringcentral_portal_access:
            raise AccessError(_('You do not have access to communication preferences.'))
        
        partner.sudo().write({
            'ringcentral_preferred_contact': post.get('preferred_contact', 'any'),
            'ringcentral_do_not_call': post.get('do_not_call') == 'on',
            'ringcentral_do_not_sms': post.get('do_not_sms') == 'on',
            'ringcentral_preferred_time': post.get('preferred_time', 'any'),
        })
        
        return request.redirect('/my/communication-preferences?saved=1')
