# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from odoo import fields, http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class RingCentralWebsiteController(http.Controller):

    def _get_client_ip(self):
        forwarded = request.httprequest.headers.get('X-Forwarded-For', '')
        if forwarded:
            return forwarded.split(',')[0].strip()
        real_ip = request.httprequest.headers.get('X-Real-IP', '')
        if real_ip:
            return real_ip.strip()
        return request.httprequest.remote_addr

    @http.route('/ringcentral/callback/request', type='json', auth='public', website=True)
    def submit_callback_request(self, **kwargs):
        """Submit a callback request from website"""
        try:
            ICP = request.env['ir.config_parameter'].sudo()
            if ICP.get_param('ringcentral_website.callback_enabled', 'True') != 'True':
                return {
                    'success': False,
                    'message': 'Callback requests are disabled',
                }

            client_ip = self._get_client_ip()
            user_agent = request.httprequest.headers.get('User-Agent')

            # Basic rate limiting (per IP per minute)
            try:
                limit_per_minute = int(ICP.get_param('ringcentral_website.callback_rate_limit_per_minute', '5') or '5')
            except Exception:
                limit_per_minute = 5

            vals = {
                'visitor_name': kwargs.get('name'),
                'visitor_phone': kwargs.get('phone'),
                'visitor_email': kwargs.get('email'),
                'subject': kwargs.get('subject'),
                'message': kwargs.get('message'),
                'preferred_time': kwargs.get('preferred_time', 'asap'),
                'source_url': kwargs.get('source_url'),
                'utm_source': kwargs.get('utm_source'),
                'utm_campaign': kwargs.get('utm_campaign'),
                'client_ip': client_ip,
                'user_agent': user_agent,
            }

            # Validate required fields early for nicer error messages
            if not vals.get('visitor_name') or not vals.get('visitor_phone'):
                return {
                    'success': False,
                    'message': 'Name and phone are required',
                }

            if limit_per_minute > 0 and client_ip:
                cutoff_dt = fields.Datetime.to_string(datetime.utcnow() - timedelta(minutes=1))
                recent_count = request.env['ringcentral.callback.request'].sudo().search_count([
                    ('client_ip', '=', client_ip),
                    ('create_date', '>=', cutoff_dt),
                ])
                if recent_count >= limit_per_minute:
                    return {
                        'success': False,
                        'message': 'Too many requests. Please try again later.',
                    }
            
            callback = request.env['ringcentral.callback.request'].sudo().create(vals)
            
            return {
                'success': True,
                'message': 'Callback request submitted successfully',
                'reference': callback.name,
            }
            
        except Exception as e:
            _logger.error(f'Callback request error: {e}')
            return {
                'success': False,
                'message': str(e),
            }

    @http.route('/ringcentral/widget/config', type='json', auth='public', website=True)
    def get_widget_config(self):
        """Get widget configuration"""
        ICP = request.env['ir.config_parameter'].sudo()
        
        return {
            'enabled': ICP.get_param('ringcentral_website.widget_enabled', 'True') == 'True',
            'show_phone': ICP.get_param('ringcentral_website.show_phone', 'True') == 'True',
            'phone_number': ICP.get_param('ringcentral_website.phone_number', ''),
            'callback_enabled': ICP.get_param('ringcentral_website.callback_enabled', 'True') == 'True',
            'position': ICP.get_param('ringcentral_website.widget_position', 'bottom-right'),
            'color': ICP.get_param('ringcentral_website.widget_color', '#007bff'),
        }

    @http.route('/ringcentral/callback', type='http', auth='public', website=True)
    def callback_page(self, **kwargs):
        """Callback request page"""
        return request.render('ringcentral_website.callback_request_page', {
            'page_title': 'Request a Callback',
        })
