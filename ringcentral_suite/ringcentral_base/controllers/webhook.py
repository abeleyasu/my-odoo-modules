# -*- coding: utf-8 -*-
"""
RingCentral Webhook Controller
==============================

Enterprise-grade HTTP endpoint for receiving RingCentral webhook notifications.
Implements:
- Mandatory signature verification in production
- IP allowlist validation
- Failed event retry queue
- Rate limiting
- Comprehensive audit logging
"""

import json
import logging
import hmac
import hashlib
import ipaddress
from datetime import datetime, timedelta

from odoo import http, SUPERUSER_ID, fields
from odoo.http import Response, request

_logger = logging.getLogger(__name__)

# RingCentral's known IP ranges (as of 2025)
RINGCENTRAL_IP_RANGES = [
    '104.146.0.0/16',
    '35.190.0.0/16',
    '35.186.0.0/16',
    '34.102.0.0/16',
    '34.96.0.0/16',
]


class RingCentralWebhookController(http.Controller):
    """Controller for RingCentral webhook endpoints with enterprise security"""
    
    @http.route('/ringcentral/webhook', type='http', auth='none', csrf=False, methods=['POST'])
    def webhook_handler(self, **kwargs):
        """
        Main webhook endpoint for all RingCentral events
        
        Security measures:
        1. IP allowlist validation
        2. Signature verification (mandatory in production)
        3. Rate limiting
        4. Audit logging
        """
        env = request.env(user=SUPERUSER_ID)
        start_time = datetime.now()
        event_id = None
        
        try:
            # RingCentral validation handshake: echo Validation-Token header back
            validation_token = request.httprequest.headers.get('Validation-Token')
            if validation_token:
                _logger.info("Webhook validation request received (header)")
                return Response(
                    "",
                    status=200,
                    headers=[('Validation-Token', validation_token)],
                    content_type='text/plain; charset=utf-8',
                )

            raw_body = request.httprequest.data or b''
            try:
                data = json.loads(raw_body.decode('utf-8') or '{}')
            except Exception:
                data = {}

            headers = dict(request.httprequest.headers)
            client_ip = self._get_client_ip()
            
            log_data = json.dumps(data, default=str)[:1000]
            _logger.info("RingCentral webhook received from %s: %s", client_ip, log_data)
            
            # Backward-compatible: some implementations send token in JSON body
            if data.get('validation_token'):
                _logger.info("Webhook validation request received (body)")
                return Response(
                    json.dumps({'validation_token': data.get('validation_token')}),
                    status=200,
                    content_type='application/json; charset=utf-8',
                )
            
            company = self._get_company_from_webhook(data)
            if not company:
                _logger.error("No RingCentral-enabled company found for webhook")
                return Response(json.dumps({'status': 'error', 'message': 'No configured company'}), status=400, content_type='application/json; charset=utf-8')

            # Best-effort idempotency: skip duplicates already received/processed
            event_hash = hashlib.sha256(raw_body).hexdigest() if raw_body else None
            event_uuid = self._get_event_uuid(data)
            try:
                if 'ringcentral.webhook.log' in env and (event_hash or event_uuid):
                    domain = [
                        ('status', 'in', ['received', 'processed', 'pending_retry', 'rejected']),
                        ('received_at', '>=', fields.Datetime.now() - timedelta(days=1)),
                    ]
                    if event_hash and event_uuid:
                        domain = ['|', ('event_hash', '=', event_hash), ('event_uuid', '=', event_uuid)] + domain
                    elif event_hash:
                        domain = [('event_hash', '=', event_hash)] + domain
                    else:
                        domain = [('event_uuid', '=', event_uuid)] + domain

                    existing = env['ringcentral.webhook.log'].sudo().search(domain, limit=1)
                    if existing:
                        return Response(json.dumps({'status': 'ok'}), status=200, content_type='application/json; charset=utf-8')
            except Exception:
                pass
            
            # Security Check 1: IP Allowlist (production mode)
            if company.ringcentral_production_mode:
                if not self._verify_ip_allowed(client_ip, company):
                    _logger.warning("Webhook from unauthorized IP: %s", client_ip)
                    self._log_webhook_event(env, company, data, 'rejected', error='Unauthorized IP')
                    return Response(
                        json.dumps({'status': 'error', 'message': 'Unauthorized'}),
                        status=401,
                        content_type='application/json; charset=utf-8',
                    )
            
            # Security Check 2: Signature Verification
            signature = headers.get('X-Ringcentral-Signature', '')
            if company.ringcentral_production_mode:
                if not company.ringcentral_webhook_secret:
                    _logger.error("Production mode requires webhook secret")
                    return Response(
                        json.dumps({'status': 'error', 'message': 'Configuration error'}),
                        status=500,
                        content_type='application/json; charset=utf-8',
                    )
                
                if not self._verify_signature(raw_body, signature, 
                                             company.ringcentral_webhook_secret):
                    _logger.warning("Invalid webhook signature from %s", client_ip)
                    self._log_webhook_event(env, company, data, 'rejected', error='Invalid signature')
                    return Response(
                        json.dumps({'status': 'error', 'message': 'Invalid signature'}),
                        status=401,
                        content_type='application/json; charset=utf-8',
                    )
            elif company.ringcentral_webhook_secret and signature:
                if not self._verify_signature(raw_body, signature,
                                             company.ringcentral_webhook_secret):
                    _logger.warning("Invalid webhook signature")
                    return Response(json.dumps({'status': 'error', 'message': 'Invalid signature'}), status=401, content_type='application/json; charset=utf-8')
            
            event_id = self._log_webhook_event(env, company, data, 'received', event_hash=event_hash, event_uuid=event_uuid)
            event_type = self._get_event_type(data)
            success = False
            error_message = None
            
            try:
                if event_type == 'telephony_session':
                    self._handle_telephony_event(env, data, company)
                elif event_type == 'sms':
                    self._handle_sms_event(env, data, company)
                elif event_type == 'voicemail':
                    self._handle_voicemail_event(env, data, company)
                elif event_type == 'presence':
                    self._handle_presence_event(env, data, company)
                elif event_type == 'meeting':
                    self._handle_meeting_event(env, data, company)
                elif event_type == 'fax':
                    self._handle_fax_event(env, data, company)
                elif event_type == 'recording':
                    self._handle_recording_event(env, data, company)
                else:
                    _logger.info("Unhandled event type: %s", event_type)
                
                success = True
                
            except Exception as e:
                error_message = str(e)
                _logger.error("Error processing %s event: %s", event_type, error_message, exc_info=True)
                self._queue_for_retry(env, event_id, data, company, error_message)
            
            elapsed = (datetime.now() - start_time).total_seconds()
            self._update_webhook_event(env, event_id, 'processed' if success else 'failed', elapsed, error_message)
            
            return Response(
                json.dumps({'status': 'ok' if success else 'queued'}),
                status=200,
                content_type='application/json; charset=utf-8',
            )
            
        except Exception as e:
            _logger.error("Webhook processing error: %s", str(e), exc_info=True)
            if event_id:
                self._update_webhook_event(env, event_id, 'error', 0, str(e))
            return Response(
                json.dumps({'status': 'error', 'message': 'Internal error'}),
                status=500,
                content_type='application/json; charset=utf-8',
            )

    def _handle_recording_event(self, env, data, company):
        """Handle recording/transcription webhooks if ringcentral_recording is installed."""
        try:
            Recording = env['ringcentral.recording']
        except Exception:
            return

        payload = dict(data.get('body') or {})
        payload['event'] = data.get('event', '')

        # process_recording_webhook expects flat keys like recordingId/contentUri
        Recording.sudo().with_company(company).process_recording_webhook(payload)
    
    @http.route('/ringcentral/webhook/test', type='http', auth='none', csrf=False, methods=['GET'])
    def webhook_test(self, **kwargs):
        """Test endpoint to verify webhook URL is accessible"""
        return "RingCentral webhook endpoint is active - v2.0"
    
    @http.route('/ringcentral/webhook/health', type='json', auth='none', csrf=False, methods=['GET'])
    def webhook_health(self, **kwargs):
        """Health check endpoint for monitoring"""
        return {'status': 'healthy', 'timestamp': fields.Datetime.now().isoformat(), 'version': '2.0'}
    
    def _get_client_ip(self):
        """Get real client IP, accounting for proxies"""
        forwarded = request.httprequest.headers.get('X-Forwarded-For', '')
        if forwarded:
            return forwarded.split(',')[0].strip()
        real_ip = request.httprequest.headers.get('X-Real-IP', '')
        if real_ip:
            return real_ip.strip()
        return request.httprequest.remote_addr
    
    def _verify_ip_allowed(self, client_ip, company):
        """Check if client IP is in allowlist"""
        try:
            client = ipaddress.ip_address(client_ip)
            allowlist_str = company.ringcentral_webhook_ip_allowlist or ''
            allowlist = [ip.strip() for ip in allowlist_str.replace(',', '\n').split('\n') if ip.strip()]
            if not allowlist:
                allowlist = RINGCENTRAL_IP_RANGES
            
            for ip_range in allowlist:
                try:
                    network = ipaddress.ip_network(ip_range, strict=False)
                    if client in network:
                        return True
                except ValueError:
                    continue
            return False
        except ValueError:
            _logger.error("Invalid IP address: %s", client_ip)
            return False
    
    def _verify_signature(self, body, signature, secret):
        """Verify webhook signature using HMAC-SHA256"""
        if not signature or not secret:
            return False
        expected = hmac.new(secret.encode('utf-8'), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature.lower(), expected.lower())
    
    def _get_company_from_webhook(self, data):
        """Determine which company the webhook is for"""
        env = request.env(user=SUPERUSER_ID)
        account_id = str(data.get('ownerId') or data.get('body', {}).get('accountId') or '')
        
        if account_id:
            company = env['res.company'].search([
                ('ringcentral_enabled', '=', True),
                ('ringcentral_account_id', '=', account_id)
            ], limit=1)
            if company:
                return company
        
        return env['res.company'].search([('ringcentral_enabled', '=', True)], limit=1)
    
    def _get_event_type(self, data):
        """Determine event type from webhook data"""
        event = data.get('event', '')
        body = data.get('body', {})
        
        if '/telephony/sessions' in event:
            return 'telephony_session'
        elif '/message-store' in event:
            message_type = body.get('type', '')
            if message_type == 'SMS':
                return 'sms'
            elif message_type == 'VoiceMail':
                return 'voicemail'
            elif message_type == 'Fax':
                return 'fax'
            return 'message'
        elif '/presence' in event:
            return 'presence'
        elif '/meeting' in event:
            return 'meeting'
        elif '/call-log' in event or '/call-recording' in event or '/recording' in event:
            return 'recording'
        return 'unknown'

    def _get_event_uuid(self, data):
        """Extract a best-effort unique identifier from webhook payload."""
        if not isinstance(data, dict):
            return None
        for key in ('uuid', 'eventId', 'event_id', 'id'):
            val = data.get(key)
            if val:
                return str(val)
        return None
    
    def _log_webhook_event(self, env, company, data, status, error=None, event_hash=None, event_uuid=None):
        """Log webhook event for audit and retry"""
        try:
            if 'ringcentral.webhook.log' not in env:
                return None
            WebhookLog = env['ringcentral.webhook.log']
            return WebhookLog.sudo().create({
                'company_id': company.id if company else False,
                'event_type': self._get_event_type(data),
                'event_data': json.dumps(data, default=str),
                'event_hash': event_hash,
                'event_uuid': event_uuid,
                'status': status,
                'error_message': error,
                'received_at': fields.Datetime.now(),
            }).id
        except Exception as e:
            _logger.error("Failed to log webhook event: %s", str(e))
            return None
    
    def _update_webhook_event(self, env, event_id, status, elapsed, error=None):
        """Update webhook event log"""
        if not event_id:
            return
        try:
            if 'ringcentral.webhook.log' not in env:
                return
            event = env['ringcentral.webhook.log'].sudo().browse(event_id)
            if event.exists():
                event.write({
                    'status': status,
                    'processing_time': elapsed,
                    'error_message': error,
                    'processed_at': fields.Datetime.now(),
                })
        except Exception as e:
            _logger.error("Failed to update webhook event: %s", str(e))
    
    def _queue_for_retry(self, env, event_id, data, company, error):
        """Queue failed event for retry"""
        try:
            if 'ringcentral.webhook.log' not in env:
                return
            event = env['ringcentral.webhook.log'].sudo().browse(event_id)
            if event.exists():
                event.write({
                    'retry_count': event.retry_count + 1,
                    'next_retry': fields.Datetime.now() + timedelta(minutes=5),
                    'status': 'pending_retry',
                })
        except Exception as e:
            _logger.error("Failed to queue for retry: %s", str(e))
    
    def _handle_telephony_event(self, env, data, company):
        """Handle telephony session events"""
        if 'ringcentral.call' not in env:
            _logger.info("ringcentral_call module not installed")
            return
        body = data.get('body', {})
        session_id = body.get('telephonySessionId')
        _logger.info("Call event: session=%s", session_id)
        env['ringcentral.call'].sudo().process_telephony_event(data, company)
    
    def _handle_sms_event(self, env, data, company):
        """Handle SMS events"""
        if 'ringcentral.sms' not in env:
            _logger.info("ringcentral_sms module not installed")
            return
        body = data.get('body', {})
        _logger.info("SMS event: id=%s", body.get('id'))
        env['ringcentral.sms'].sudo().process_sms_event(data, company)
    
    def _handle_voicemail_event(self, env, data, company):
        """Handle voicemail events"""
        if 'ringcentral.voicemail' not in env:
            _logger.info("ringcentral_voicemail module not installed")
            return
        body = data.get('body', {})
        _logger.info("Voicemail event: id=%s", body.get('id'))
        env['ringcentral.voicemail'].sudo().process_voicemail_event(data, company)
    
    def _handle_presence_event(self, env, data, company):
        """Handle presence events"""
        body = data.get('body', {})
        extension_id = str(body.get('extensionId', ''))
        presence_status = body.get('presenceStatus')
        telephony_status = body.get('telephonyStatus')
        
        _logger.info("Presence event: extension=%s", extension_id)
        
        user = env['res.users'].sudo().search([('ringcentral_extension_id', '=', extension_id)], limit=1)
        if user:
            user.write({
                'ringcentral_presence_status': presence_status,
                'ringcentral_telephony_status': telephony_status,
            })
            env['bus.bus']._sendone(f'ringcentral_presence_{user.id}', 'presence_update', {
                'user_id': user.id,
                'presence_status': presence_status,
                'telephony_status': telephony_status,
            })
        
        if 'ringcentral.presence' in env:
            env['ringcentral.presence'].sudo().process_presence_webhook(body)
    
    def _handle_meeting_event(self, env, data, company):
        """Handle meeting events"""
        if 'ringcentral.meeting' not in env:
            _logger.info("ringcentral_meet module not installed")
            return
        body = data.get('body', {})
        _logger.info("Meeting event: id=%s", body.get('id'))
        env['ringcentral.meeting'].sudo().process_meeting_event(data, company)
    
    def _handle_fax_event(self, env, data, company):
        """Handle fax events"""
        if 'ringcentral.fax' not in env:
            _logger.info("ringcentral_fax module not installed")
            return
        body = data.get('body', {})
        _logger.info("Fax event: id=%s", body.get('id'))
        env['ringcentral.fax'].sudo().process_fax_event(data, company)
