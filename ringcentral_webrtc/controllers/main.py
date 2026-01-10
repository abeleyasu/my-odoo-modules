# -*- coding: utf-8 -*-

from odoo import http, fields
from odoo.http import request
from markupsafe import Markup
import logging
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class RingCentralWebRTCController(http.Controller):

    def _get_company_config(self):
        """Get RingCentral configuration from the appropriate company"""
        # Try to get company from user context first
        if request.env.user and request.env.user.company_id:
            company = request.env.user.company_id.sudo()
        else:
            # Fall back to website company or main company for public access
            if hasattr(request, 'website') and request.website:
                company = request.website.company_id.sudo()
            else:
                company = request.env['res.company'].sudo().search(
                    [('ringcentral_enabled', '=', True)], 
                    limit=1
                )
                if not company:
                    company = request.env['res.company'].sudo().search([], limit=1)
        return company

    @http.route('/ringcentral/test', type='http', auth='user', website=False)
    def test_widget_page(self):
        """Serve a test page to verify RingCentral Embeddable widget works"""
        if not request.env.user.has_group('ringcentral_base.group_ringcentral_admin'):
            return request.not_found()

        # Get client_id from company using proper multi-company logic
        company = self._get_company_config()
        client_id = company.ringcentral_client_id or ''
        server_url = company.ringcentral_server_url or 'https://platform.ringcentral.com'
        
        html = f'''<!DOCTYPE html>
<html>
<head>
    <title>RingCentral Widget Test</title>
    <style>
        body {{ font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5; }}
        .info {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; }}
        .success {{ color: green; }}
        .error {{ color: red; }}
        .warning {{ color: orange; }}
        pre {{ background: #eee; padding: 10px; border-radius: 4px; }}
        button {{ background: #0073ea; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; margin: 5px; }}
        button:hover {{ background: #0056b3; }}
        #log {{ background:#fff; padding:10px; border:1px solid #ddd; height:200px; overflow-y:auto; font-family:monospace; font-size:12px; }}
    </style>
</head>
<body>
    <div class="info">
        <h1>RingCentral Widget Test Page</h1>
        
        <h3>Configuration:</h3>
        <pre>
Client ID: {client_id[:10]}... (from Odoo settings)
Server: {server_url}
Redirect URI: https://apps.ringcentral.com/integration/ringcentral-embeddable/latest/redirect.html
        </pre>
        
        <h3>Status:</h3>
        <div id="status">Loading widget...</div>
        
        <h3>Actions:</h3>
        <button onclick="showWidget()">Show Widget</button>
        <button onclick="hideWidget()">Hide Widget</button>
        <button onclick="testCall()">Test Call</button>
        
        <h3>Instructions:</h3>
        <ol>
            <li>Look for the RingCentral phone icon in the <b>bottom-right corner</b></li>
            <li>Click the icon to expand the widget</li>
            <li>Click "Sign In" - a popup should appear</li>
            <li>If no popup appears, <b>check your browser's popup blocker</b></li>
            <li>Allow popups for this site and try again</li>
        </ol>
        
        <h3>Events Log:</h3>
        <div id="log"></div>
    </div>

    <script>
        function log(msg, type) {{
            var logDiv = document.getElementById('log');
            var time = new Date().toLocaleTimeString();
            var color = type === 'error' ? 'red' : type === 'success' ? 'green' : 'black';
            logDiv.innerHTML = '<div style="color:'+color+'">['+time+'] '+msg+'</div>' + logDiv.innerHTML;
        }}
        
        function updateStatus(msg, cls) {{
            document.getElementById('status').innerHTML = '<span class="'+cls+'">'+msg+'</span>';
        }}

        window.addEventListener('message', function(e) {{
            if (e.data && e.data.type) {{
                log('Event: ' + e.data.type, 'info');
                if (e.data.type === 'rc-login-status-notify') {{
                    if (e.data.loggedIn) {{
                        updateStatus('✅ Logged in!', 'success');
                        log('Login successful!', 'success');
                    }} else {{
                        updateStatus('⚠️ Not logged in', 'warning');
                    }}
                }}
                if (e.data.type === 'rc-login-popup-notify') {{
                    log('Login popup opened: ' + e.data.oAuthUri, 'info');
                }}
            }}
        }});

        function showWidget() {{
            window.postMessage({{ type: 'rc-adapter-minimize', minimize: false }}, '*');
        }}
        function hideWidget() {{
            window.postMessage({{ type: 'rc-adapter-minimize', minimize: true }}, '*');
        }}
        function testCall() {{
            window.postMessage({{ type: 'rc-adapter-new-call', phoneNumber: '5551234', toCall: true }}, '*');
        }}

        // Load widget
        log('Loading RingCentral widget...', 'info');
        var s = document.createElement('script');
        s.src = 'https://apps.ringcentral.com/integration/ringcentral-embeddable/latest/adapter.js?' +
            'clientId={client_id}' +
            '&appServer={server_url}' +
            '&redirectUri=https://apps.ringcentral.com/integration/ringcentral-embeddable/latest/redirect.html' +
            '&minimized=false';  // Start expanded to see Sign In button
        s.onload = function() {{
            log('Widget loaded!', 'success');
            updateStatus('⏳ Look for phone widget in bottom-right corner', 'warning');
        }};
        s.onerror = function() {{ log('Failed to load!', 'error'); }};
        document.body.appendChild(s);
    </script>
</body>
</html>'''
        return request.make_response(html, headers=[('Content-Type', 'text/html')])

    @http.route('/ringcentral/webrtc/config', type='json', auth='user')
    def get_webrtc_config(self):
        """Get WebRTC configuration for softphone"""
        return request.env.user.get_webrtc_config()

    @http.route('/ringcentral/embeddable/config', type='json', auth='user')
    def get_embeddable_config(self):
        """Get RingCentral Embeddable widget configuration"""
        company = request.env.company
        
        # Check if RingCentral is enabled
        if not company.ringcentral_enabled:
            return {'enabled': False, 'error': 'RingCentral is not enabled'}
        
        # Get credentials
        client_id = company.ringcentral_client_id
        client_secret = company.ringcentral_client_secret
        jwt_token = company.ringcentral_jwt_token
        server_url = company.ringcentral_server_url or 'https://platform.ringcentral.com'
        
        if not client_id:
            return {'enabled': False, 'error': 'RingCentral client ID not configured'}
        
        return {
            'enabled': True,
            'client_id': client_id,
            'client_secret': client_secret,  # Needed for JWT auth
            'server_url': server_url,
            'jwt_token': jwt_token,  # For auto-login
        }

    @http.route('/ringcentral/embeddable/auth', type='json', auth='user')
    def get_embeddable_auth(self):
        """Get access token for RingCentral Embeddable widget using JWT"""
        company = request.env.company
        
        if not company.ringcentral_enabled:
            return {'success': False, 'error': 'RingCentral is not enabled'}
        
        jwt_token = company.ringcentral_jwt_token
        if not jwt_token:
            return {'success': False, 'error': 'JWT token not configured'}
        
        try:
            # Use the API service to get authenticated platform
            api = request.env['ringcentral.api']
            platform = api._get_platform(company)
            
            # Get the access token from the authenticated platform
            auth = platform.auth()
            access_token = auth.access_token()
            refresh_token = auth.refresh_token()
            token_type = auth.token_type() if hasattr(auth, 'token_type') else 'Bearer'
            expires_in = auth.expires_in() if hasattr(auth, 'expires_in') else 3600
            
            return {
                'success': True,
                'access_token': access_token,
                'refresh_token': refresh_token,
                'token_type': token_type,
                'expires_in': expires_in,
                'owner_id': auth.data().get('owner_id') if hasattr(auth, 'data') else None,
            }
        except Exception as e:
            _logger.error(f'Failed to get RingCentral auth token: {e}')
            return {'success': False, 'error': str(e)}

    @http.route('/ringcentral/call/log-start', type='json', auth='user')
    def log_call_start(self, phone_number, direction='outbound', session_id=None, call_id=None, party_id=None, ringout_id=None, res_model=None, res_id=None, contact_name=None):
        """Log call start from RingCentral Embeddable widget"""
        try:
            # Normalize direction to lowercase for database selection field
            direction = (direction or 'outbound').lower()
            
            _logger.info(f"RingCentral log-start: phone={phone_number}, session={session_id}, call_id={call_id}, party_id={party_id}")
            
            # Try to find partner by phone number
            partner = request.env['res.partner'].search([
                '|',
                ('phone', 'ilike', phone_number),
                ('mobile', 'ilike', phone_number),
            ], limit=1)
            
            call_vals = {
                'phone_number': phone_number,
                'partner_id': partner.id if partner else None,
                'direction': direction,
                'state': 'ringing',
                'user_id': request.env.user.id,
                'call_source': 'embeddable',
                'ringcentral_session_id': session_id,
                'ringcentral_call_id': call_id,
                'ringcentral_party_id': party_id,
                'ringout_id': ringout_id,
            }
            if res_model and res_id:
                call_vals.update({
                    'res_model': res_model,
                    'res_id': res_id,
                })
            if contact_name:
                call_vals['caller_id_name'] = contact_name

            call = None
            if session_id:
                call = request.env['ringcentral.call'].search([
                    ('ringcentral_session_id', '=', session_id),
                    ('ringcentral_session_id', '!=', False),
                ], limit=1, order='id desc')

            # Fallback idempotency: some widget events do not include a session id.
            # In that case, reuse a very recent "ringing" call for this user/number/context.
            if not call and not session_id:
                recent_domain = [
                    ('user_id', '=', request.env.user.id),
                    ('call_source', '=', 'embeddable'),
                    ('phone_number', '=', phone_number),
                    ('state', 'in', ['pending', 'ringing', 'answered', 'on_hold']),
                    ('create_date', '>=', fields.Datetime.to_string(fields.Datetime.now() - relativedelta(minutes=2))),
                ]
                if res_model and res_id:
                    recent_domain += [
                        ('res_model', '=', res_model),
                        ('res_id', '=', res_id),
                    ]
                call = request.env['ringcentral.call'].search(recent_domain, limit=1, order='id desc')

            if call:
                # Keep the same call record for the same RC session_id
                update_vals = {}
                for key, value in call_vals.items():
                    if value and (not getattr(call, key, False)):
                        update_vals[key] = value
                # Always ensure state is at least ringing when we get a start event
                update_vals['state'] = 'ringing'
                if update_vals:
                    call.write(update_vals)
            else:
                call = request.env['ringcentral.call'].create(call_vals)

            # Post to chatter that the call was initiated (idempotent)
            if not call.chatter_start_posted:
                self._post_call_started(call)
                call.sudo().write({'chatter_start_posted': True})
            return {'success': True, 'call_id': call.id}
        except Exception as e:
            _logger.error(f'Failed to log call start: {e}')
            return {'success': False, 'error': str(e)}

    @http.route('/ringcentral/call/log-attempt', type='json', auth='user')
    def log_call_attempt(self, phone_number, res_model=None, res_id=None, contact_name=None):
        """Log a call attempt (click) to chatter immediately"""
        try:
            if not res_model or not res_id:
                return {'success': False, 'reason': 'no_context'}
                
            record = request.env[res_model].browse(res_id)
            if not record.exists():
                return {'success': False, 'reason': 'record_not_found'}
                
            # Check if the model has message_post (inherits mail.thread)
            if hasattr(record, 'message_post'):
                body = f"Initiating call to {contact_name or phone_number}..."
                recent = request.env['mail.message'].sudo().search_count([
                    ('model', '=', record._name),
                    ('res_id', '=', record.id),
                    ('author_id', '=', request.env.user.partner_id.id),
                    ('body', 'ilike', body),
                    ('create_date', '>=', fields.Datetime.to_string(fields.Datetime.now() - relativedelta(minutes=2))),
                ])
                if not recent:
                    record.message_post(body=body, message_type='notification', subtype_xmlid='mail.mt_note')
                return {'success': True}
                
            return {'success': False, 'reason': 'no_chatter'}
        except Exception as e:
            _logger.error(f'Failed to log call attempt: {e}')
            return {'success': False, 'error': str(e)}

    @http.route('/ringcentral/call/log-end', type='json', auth='user')
    def log_call_end(self, session_id=None, call_id=None, party_id=None, recording_id=None, duration=None, result=None, res_model=None, res_id=None):
        """Log call end from RingCentral Embeddable widget and post to chatter"""
        try:
            _logger.info(f"RingCentral log-end: session={session_id}, call_id={call_id}, party_id={party_id}, recording_id={recording_id}, duration={duration}, result={result}")
            
            call = None
            if session_id:
                call = request.env['ringcentral.call'].search([
                    ('ringcentral_session_id', '=', session_id),
                ], limit=1, order='id desc')
            
            if not call and call_id:
                call = request.env['ringcentral.call'].search([
                    ('ringcentral_call_id', '=', call_id),
                ], limit=1, order='id desc')
            
            if not call:
                # Find most recent call for this user
                call = request.env['ringcentral.call'].search([
                    ('user_id', '=', request.env.user.id),
                    ('state', 'in', ['ringing', 'answered', 'on_hold']),
                ], limit=1, order='id desc')
            
            if call:
                vals = {
                    'state': 'ended',
                    'end_time': fields.Datetime.now(),
                }
                if duration:
                    vals['duration'] = int(duration)
                if result:
                    # Map common RingCentral result values to our selection field
                    result_map = {
                        'Completed': 'answered',
                        'NoAnswer': 'no_answer',
                        'Busy': 'busy',
                        'Rejected': 'rejected',
                        'Voicemail': 'voicemail',
                        'Failed': 'failed',
                        'Cancelled': 'cancelled',
                        'CallConnected': 'answered',
                        'CallFailed': 'failed',
                    }
                    vals['call_result'] = result_map.get(result, 'answered')
                
                # Update any missing IDs
                if call_id and not call.ringcentral_call_id:
                    vals['ringcentral_call_id'] = call_id
                if party_id and not call.ringcentral_party_id:
                    vals['ringcentral_party_id'] = party_id
                if session_id and not call.ringcentral_session_id:
                    vals['ringcentral_session_id'] = session_id
                    
                call.write(vals)
                
                # If recording_id is provided, schedule recording fetch
                if recording_id:
                    _logger.info(f"Recording ID received: {recording_id} - scheduling fetch")
                    # TODO: Trigger async recording fetch
                
                # Post to chatter on the related record (idempotent)
                if not call.chatter_end_posted:
                    self._post_call_to_chatter(call)
                    call.sudo().write({'chatter_end_posted': True})
                
                return {'success': True, 'call_id': call.id}
            
            return {'success': False, 'error': 'Call not found'}
        except Exception as e:
            _logger.error(f'Failed to log call end: {e}')
            return {'success': False, 'error': str(e)}
    
    def _post_call_to_chatter(self, call):
        """Post call summary to the related record's chatter"""
        try:
            # Determine the record to post to
            record = None
            if call.res_model and call.res_id:
                try:
                    record = request.env[call.res_model].browse(call.res_id)
                    if not record.exists():
                        record = None
                except Exception:
                    record = None
            
            # Fallback to partner if no specific record
            if not record and call.partner_id:
                record = call.partner_id
            
            if record and hasattr(record, 'message_post'):
                # Format duration
                duration_str = "0:00"
                if call.duration:
                    minutes, seconds = divmod(call.duration, 60)
                    hours, minutes = divmod(minutes, 60)
                    if hours:
                        duration_str = f"{hours}:{minutes:02d}:{seconds:02d}"
                    else:
                        duration_str = f"{minutes}:{seconds:02d}"
                
                # Determine direction icon and label
                direction_icon = "📞" if call.direction == 'outbound' else "📲"
                direction_label = "Outbound" if call.direction == 'outbound' else "Inbound"
                result_label = dict(call._fields['call_result'].selection).get(call.call_result, call.call_result or 'Completed')
                
                # Build call record URL
                call_url = self._get_call_record_url(call)
                
                # Build HTML body with button
                body = f"""
                <div style="padding: 8px 0;">
                    <strong>{direction_icon} {direction_label} Call Ended</strong><br/>
                    <table style="margin: 8px 0; border-collapse: collapse;">
                        <tr><td style="padding: 2px 8px 2px 0; color: #666;">Phone:</td><td>{call.phone_number}</td></tr>
                        <tr><td style="padding: 2px 8px 2px 0; color: #666;">Duration:</td><td>{duration_str}</td></tr>
                        <tr><td style="padding: 2px 8px 2px 0; color: #666;">Result:</td><td>{result_label}</td></tr>
                        <tr><td style="padding: 2px 8px 2px 0; color: #666;">Agent:</td><td>{call.user_id.name}</td></tr>
                    </table>
                    <a href="{call_url}" style="display: inline-block; padding: 6px 12px; background: #714B67; color: white; text-decoration: none; border-radius: 4px; font-size: 13px;">
                        📋 View Call Details
                    </a>
                </div>
                """
                
                record.message_post(
                    body=Markup(body),
                    message_type='notification',
                    subtype_xmlid='mail.mt_note',
                )
                _logger.info(f'Posted call summary to {call.res_model}/{call.res_id}')
        except Exception as e:
            _logger.warning(f'Failed to post call to chatter: {e}')

    def _post_call_started(self, call):
        """Post a chatter note when a call is initiated"""
        try:
            record = self._get_chatter_record_for_call(call)
            if not record or not hasattr(record, 'message_post'):
                return

            start_time = fields.Datetime.context_timestamp(request.env.user, fields.Datetime.now())
            call_url = self._get_call_record_url(call)
            
            # Build HTML body with button
            body = f"""
            <div style="padding: 8px 0;">
                <strong>📞 Call Initiated</strong><br/>
                <table style="margin: 8px 0; border-collapse: collapse;">
                    <tr><td style="padding: 2px 8px 2px 0; color: #666;">Agent:</td><td>{call.user_id.name}</td></tr>
                    <tr><td style="padding: 2px 8px 2px 0; color: #666;">Phone:</td><td>{call.phone_number}</td></tr>
                    <tr><td style="padding: 2px 8px 2px 0; color: #666;">Time:</td><td>{start_time.strftime('%Y-%m-%d %H:%M')}</td></tr>
                </table>
                <a href="{call_url}" style="display: inline-block; padding: 6px 12px; background: #875A7B; color: white; text-decoration: none; border-radius: 4px; font-size: 13px;">
                    📋 View Call Record
                </a>
            </div>
            """
            
            record.message_post(
                body=Markup(body),
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
        except Exception as e:
            _logger.warning(f'Failed to post call start to chatter: {e}')

    def _get_chatter_record_for_call(self, call):
        """Return the record where chatter posts should be written."""
        record = None
        if call.res_model and call.res_id:
            try:
                record = request.env[call.res_model].browse(call.res_id)
                if not record.exists():
                    record = None
            except Exception:
                record = None
        if not record and call.partner_id:
            record = call.partner_id
        return record

    def _get_call_record_url(self, call):
        """Build an absolute URL to the ringcentral.call record in Odoo."""
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base_url}/web#id={call.id}&model=ringcentral.call&view_type=form"

    @http.route('/ringcentral/webrtc/save_devices', type='json', auth='user')
    def save_audio_devices(self, input_device, output_device, ringtone_device):
        """Save audio device preferences"""
        return request.env.user.save_audio_devices(
            input_device, output_device, ringtone_device
        )

    @http.route('/ringcentral/webrtc/call/start', type='json', auth='user')
    def start_call(self, phone_number, partner_id=None):
        """Log outbound call start"""
        try:
            call = request.env['ringcentral.call'].create({
                'phone_number': phone_number,
                'partner_id': partner_id,
                'direction': 'outbound',
                'state': 'ringing',
                'user_id': request.env.user.id,
                'call_source': 'webrtc',
            })
            return {'success': True, 'call_id': call.id}
        except Exception as e:
            _logger.error(f'Failed to log call: {e}')
            return {'success': False, 'error': str(e)}

    @http.route('/ringcentral/webrtc/call/update', type='json', auth='user')
    def update_call(self, call_id, state=None, duration=None):
        """Update call status"""
        try:
            call = request.env['ringcentral.call'].browse(call_id)
            if call.exists():
                vals = {}
                if state:
                    vals['state'] = state
                if duration:
                    vals['duration'] = duration
                if vals:
                    call.write(vals)
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
