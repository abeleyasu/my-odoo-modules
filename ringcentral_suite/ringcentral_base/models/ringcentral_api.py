# -*- coding: utf-8 -*-
"""
RingCentral API Service
=======================

Enterprise-grade API wrapper providing:
- Authentication (JWT and OAuth 2.0) with token caching
- API calls with intelligent retry logic
- Rate limit handling with backoff
- Comprehensive error management
- Health monitoring and metrics
- Thread-safe token management
"""

import logging
import time
import json
import hashlib
import hmac
import threading
import base64
import urllib.parse
from datetime import datetime, timedelta
from io import BytesIO

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

try:
    from ringcentral import SDK
    RINGCENTRAL_AVAILABLE = True
except ImportError:
    RINGCENTRAL_AVAILABLE = False
    _logger.warning("ringcentral package not installed. Please run: pip install ringcentral")

try:
    import requests
    from requests_toolbelt import MultipartEncoder
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    _logger.warning("requests or requests_toolbelt not installed")


class RingCentralAPI(models.AbstractModel):
    """RingCentral API Service - Enterprise SDK Wrapper with Token Caching"""
    
    _name = 'ringcentral.api'
    _description = 'RingCentral API Service'
    
    # Thread-safe token cache
    _platform_cache = {}
    _cache_lock = threading.Lock()
    _token_expiry = {}
    
    # ===========================
    # Configuration (from company)
    # ===========================
    
    def _get_config(self, company=None):
        """Get API configuration from company settings"""
        company = company or self.env.company
        return {
            'max_retries': company.ringcentral_max_retries or 3,
            'retry_delay': company.ringcentral_retry_delay or 1,
            'rate_limit_wait': company.ringcentral_rate_limit_wait or 60,
        }
    
    # ===========================
    # SDK and Authentication
    # ===========================
    
    @api.model
    def _get_sdk(self, company=None):
        """Get RingCentral SDK instance"""
        if not RINGCENTRAL_AVAILABLE:
            raise UserError(_("RingCentral SDK not installed. Please run: pip install ringcentral"))
        
        company = company or self.env.company
        
        client_id = company.ringcentral_client_id
        client_secret = company.ringcentral_client_secret
        server_url = company.ringcentral_server_url or 'https://platform.ringcentral.com'
        
        if not client_id:
            raise UserError(_("RingCentral Client ID not configured. Please go to Settings > RingCentral."))
        
        if not client_secret:
            raise UserError(_("RingCentral Client Secret not configured. Please go to Settings > RingCentral."))
        
        sdk = SDK(client_id, client_secret, server_url)
        return sdk
    
    @api.model
    def _get_cache_key(self, company):
        """Generate cache key for platform instance"""
        return f"platform_{company.id}_{company.write_date}"
    
    @api.model
    def _get_platform(self, company=None, force_refresh=False):
        """
        Get authenticated RingCentral platform instance with token caching.
        
        Thread-safe implementation that caches authenticated platform instances
        to avoid repeated authentication calls.
        """
        company = company or self.env.company
        cache_key = self._get_cache_key(company)
        
        with self._cache_lock:
            # Check if we have a valid cached platform
            if not force_refresh and cache_key in self._platform_cache:
                platform = self._platform_cache[cache_key]
                expiry = self._token_expiry.get(cache_key)
                
                # Check if token is still valid (with 5 min buffer)
                if expiry and datetime.now() < expiry - timedelta(minutes=5):
                    try:
                        if platform.logged_in():
                            return platform
                    except Exception:
                        pass  # Token invalid, will re-authenticate
                
                # Try to refresh the token
                try:
                    platform.refresh()
                    self._token_expiry[cache_key] = datetime.now() + timedelta(hours=1)
                    return platform
                except Exception:
                    pass  # Refresh failed, will re-authenticate
        
        # Need to authenticate
        platform = self._authenticate(company)
        
        with self._cache_lock:
            self._platform_cache[cache_key] = platform
            self._token_expiry[cache_key] = datetime.now() + timedelta(hours=1)
        
        return platform
    
    @api.model
    def _authenticate(self, company):
        """Authenticate with RingCentral and return platform instance"""
        sdk = self._get_sdk(company)
        platform = sdk.platform()
        
        # Try JWT authentication first (preferred)
        jwt_token = company.ringcentral_jwt_token
        if jwt_token:
            try:
                platform.login(jwt=jwt_token)
                _logger.info("RingCentral JWT authentication successful for company %s", company.name)
                
                # Sync account ID for webhook routing
                self._sync_account_id(company, platform)
                
                return platform
            except Exception as e:
                error_msg = str(e)
                _logger.error("RingCentral JWT authentication failed: %s", error_msg)
                self._log_api_call('auth', 'jwt_login', {}, error=error_msg)
                raise UserError(_("RingCentral JWT authentication failed: %s") % error_msg)
        
        # Fallback to OAuth password grant
        username = company.ringcentral_username
        password = company.ringcentral_password
        extension = company.ringcentral_extension or ''
        
        if username and password:
            try:
                platform.login(
                    username=username,
                    password=password,
                    extension=extension
                )
                _logger.info("RingCentral OAuth authentication successful for company %s", company.name)
                
                # Sync account ID for webhook routing
                self._sync_account_id(company, platform)
                
                return platform
            except Exception as e:
                error_msg = str(e)
                _logger.error("RingCentral OAuth authentication failed: %s", error_msg)
                self._log_api_call('auth', 'oauth_login', {}, error=error_msg)
                raise UserError(_("RingCentral OAuth authentication failed: %s") % error_msg)
        
        raise UserError(_("RingCentral authentication not configured. Please provide JWT token or OAuth credentials."))
    
    @api.model
    def _sync_account_id(self, company, platform):
        """Sync RingCentral account ID to company for webhook routing"""
        try:
            response = platform.get('/restapi/v1.0/account/~')
            account_info = json.loads(response.text()) if response.text() else {}
            account_id = str(account_info.get('id', ''))
            
            if account_id and account_id != company.ringcentral_account_id:
                company.sudo().write({'ringcentral_account_id': account_id})
                _logger.info("Synced RingCentral account ID %s for company %s", account_id, company.name)
        except Exception as e:
            _logger.warning("Failed to sync account ID: %s", str(e))
    
    @api.model
    def clear_token_cache(self, company=None):
        """Clear cached tokens (call after credential changes)"""
        with self._cache_lock:
            if company:
                cache_key = self._get_cache_key(company)
                self._platform_cache.pop(cache_key, None)
                self._token_expiry.pop(cache_key, None)
            else:
                self._platform_cache.clear()
                self._token_expiry.clear()
        _logger.info("Cleared RingCentral token cache")

    
    @api.model
    def _api_call(self, method, endpoint, params=None, body=None, company=None, files=None):
        """
        Make an API call to RingCentral with retry logic
        
        :param method: HTTP method (GET, POST, PUT, DELETE)
        :param endpoint: API endpoint path
        :param params: Query parameters
        :param body: Request body (JSON data)
        :param company: Company record (optional)
        :param files: List of file tuples for multipart uploads [(filename, content, content_type)]
        :return: API response
        """
        company = company or self.env.company
        platform = self._get_platform(company)
        config = self._get_config(company)
        
        max_retries = config['max_retries']
        retry_delay = config['retry_delay']
        rate_limit_wait = config['rate_limit_wait']
        
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                
                # Handle multipart file uploads (MMS, Fax)
                if files and method.upper() == 'POST':
                    response = self._multipart_post(platform, endpoint, body, files, company)
                elif method.upper() == 'GET':
                    response = platform.get(endpoint, params)
                elif method.upper() == 'POST':
                    response = platform.post(endpoint, body)
                elif method.upper() == 'PUT':
                    response = platform.put(endpoint, body)
                elif method.upper() == 'DELETE':
                    response = platform.delete(endpoint)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                elapsed = time.time() - start_time
                
                # Handle response - could be SDK response or requests response
                if hasattr(response, 'text'):
                    # SDK response
                    response_text = response.text() if callable(response.text) else response.text
                elif hasattr(response, 'json'):
                    # Requests response
                    response_text = response.text
                else:
                    response_text = str(response)
                
                result = json.loads(response_text) if response_text else {}
                
                # Log successful call
                self._log_api_call(method, endpoint, params or body or {}, 
                                   response_data=result, elapsed=elapsed)
                
                return result
                
            except Exception as e:
                error_str = str(e)
                _logger.warning(
                    "RingCentral API call failed (attempt %d/%d): %s %s - %s",
                    attempt + 1, max_retries, method, endpoint, error_str
                )
                
                # Check for rate limit (429 Too Many Requests)
                if 'rate limit' in error_str.lower() or '429' in error_str:
                    wait_time = rate_limit_wait * (attempt + 1)
                    _logger.info("Rate limited, waiting %d seconds", wait_time)
                    time.sleep(wait_time)
                    # Force token refresh in case of stale token
                    platform = self._get_platform(company, force_refresh=True)
                    continue
                
                # Check for auth errors - refresh token
                if '401' in error_str or 'unauthorized' in error_str.lower():
                    _logger.info("Auth error, refreshing token...")
                    platform = self._get_platform(company, force_refresh=True)
                    continue
                
                # Retry on connection errors
                if 'connection' in error_str.lower() or 'timeout' in error_str.lower():
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    time.sleep(wait_time)
                    continue
                
                # Log error and raise on final attempt
                self._log_api_call(method, endpoint, params or body or {}, error=error_str)
                
                if attempt == max_retries - 1:
                    raise UserError(_("RingCentral API error: %s") % error_str)
        
        raise UserError(_("RingCentral API call failed after %d attempts") % max_retries)

    # ===========================
    # Token / Binary helpers
    # ===========================

    @api.model
    def get_access_token(self, company=None, force_refresh=False):
        """Return current access token for the given company."""
        company = company or self.env.company
        platform = self._get_platform(company, force_refresh=force_refresh)

        try:
            auth_data = platform.auth().data()
            token = auth_data.get('access_token')
        except Exception:
            token = platform._token.access_token if hasattr(platform, '_token') else None

        if not token:
            raise UserError(_("Unable to retrieve RingCentral access token"))
        return token

    @api.model
    def _add_access_token_to_url(self, url, company=None):
        """Append access_token query param to a URL (used for RingCentral AI contentUri ingestion)."""
        token = self.get_access_token(company=company)
        parsed = urllib.parse.urlparse(url)
        query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        if 'access_token' not in query:
            query['access_token'] = [token]
        new_query = urllib.parse.urlencode(query, doseq=True)
        return urllib.parse.urlunparse(parsed._replace(query=new_query))

    @api.model
    def download_recording(self, content_uri, company=None, timeout=60):
        """Download binary recording content from RingCentral (does not store in Odoo)."""
        if not REQUESTS_AVAILABLE:
            raise UserError(_("requests package required to download recordings. Install with: pip install requests"))

        company = company or self.env.company
        token = self.get_access_token(company=company)

        resp = requests.get(
            content_uri,
            headers={
                'Authorization': f'Bearer {token}',
            },
            timeout=timeout,
            stream=True,
        )
        if resp.status_code >= 400:
            raise UserError(_("RingCentral recording download failed: HTTP %s") % resp.status_code)

        content_type = resp.headers.get('Content-Type') or 'application/octet-stream'
        return resp.content, content_type

    # ===========================
    # Call Log helpers
    # ===========================

    @api.model
    def find_recordings_for_telephony_session(self, telephony_session_id, company=None, date_from=None, date_to=None):
        """Find call-log entries with recordings for a given telephonySessionId."""
        if not telephony_session_id:
            return []

        params = {
            'view': 'Detailed',
            'perPage': 100,
            'recordingType': 'All',
        }
        if date_from:
            params['dateFrom'] = date_from
        if date_to:
            params['dateTo'] = date_to

        result = self.get_call_log(params=params, company=company)
        records = result.get('records', []) if isinstance(result, dict) else []
        matched = []
        for item in records:
            item_session = item.get('telephonySessionId') or item.get('sessionId')
            if str(item_session or '') != str(telephony_session_id):
                continue
            recording = item.get('recording') or {}
            content_uri = recording.get('contentUri')
            rec_id = recording.get('id')
            if rec_id and content_uri:
                matched.append({
                    'call_log': item,
                    'recording': recording,
                })
        return matched

    # ===========================
    # Transcription helpers
    # ===========================

    @api.model
    def request_transcription(self, recording_id, content_uri=None, language='en-US', company=None):
        """Request transcription for a recording. Tries call-log transcription first, falls back to AI async STT."""
        # 1) Try RingCentral call-log transcription (if enabled on the account)
        try:
            result = self.get_call_transcription(recording_id, company=company)
            text = result.get('text') or result.get('transcript')
            if text:
                return {'transcription': text}
        except Exception:
            pass

        # 2) Fallback: RingCentral AI async speech-to-text using contentUri
        if not content_uri:
            return {}

        stt_body = {
            'contentUri': self._add_access_token_to_url(content_uri, company=company),
            'languageCode': language or 'en-US',
            # Best-effort defaults; RingCentral will infer in many cases
            'encoding': 'MP3',
            'enablePunctuation': True,
        }

        result = self._api_call('POST', '/ai/audio/v1/async/speech-to-text', body=stt_body, company=company)
        job_id = (result or {}).get('jobId')
        if job_id:
            return {'jobId': job_id}
        return result or {}

    @api.model
    def get_transcription_job(self, job_id, company=None):
        """Fetch RingCentral AI async STT job result."""
        if not job_id:
            return {}

        # Most common pattern is /{jobId}
        try:
            return self._api_call('GET', f'/ai/audio/v1/async/speech-to-text/{job_id}', company=company)
        except Exception:
            # Fallback (if API expects jobId as query parameter)
            return self._api_call('GET', '/ai/audio/v1/async/speech-to-text', params={'jobId': job_id}, company=company)
    
    @api.model
    def _multipart_post(self, platform, endpoint, json_body, files, company=None):
        """
        Handle multipart/form-data POST requests for MMS and Fax
        
        :param platform: Authenticated platform instance
        :param endpoint: API endpoint
        :param json_body: JSON metadata for the request
        :param files: List of (filename, content, content_type) tuples
        :return: Response
        """
        if not REQUESTS_AVAILABLE:
            raise UserError(_("requests and requests_toolbelt packages required for file uploads. Install with: pip install requests requests-toolbelt"))
        
        company = company or self.env.company
        base_url = company.ringcentral_server_url or 'https://platform.ringcentral.com'
        full_url = f"{base_url}{endpoint}"
        
        # Get the access token from the platform
        try:
            auth_data = platform.auth().data()
            access_token = auth_data.get('access_token')
        except Exception:
            # Fallback for different SDK versions
            access_token = platform._token.access_token if hasattr(platform, '_token') else None
        
        if not access_token:
            raise UserError(_("Unable to retrieve access token for file upload"))
        
        # Build multipart form data
        fields = []
        
        # Add JSON body as first part
        fields.append(('json', (None, json.dumps(json_body), 'application/json')))
        
        # Add file attachments
        for filename, content, content_type in files:
            # Handle base64 encoded content
            if isinstance(content, str):
                try:
                    content = base64.b64decode(content)
                except Exception:
                    content = content.encode('utf-8')
            
            fields.append(('attachment', (filename, BytesIO(content), content_type)))
        
        # Create multipart encoder
        encoder = MultipartEncoder(fields=fields)
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': encoder.content_type,
        }
        
        response = requests.post(full_url, data=encoder, headers=headers, timeout=120)
        
        if response.status_code >= 400:
            raise UserError(_("File upload failed: %s - %s") % (response.status_code, response.text))
        
        return response
    
    @api.model
    def _log_api_call(self, method, endpoint, request_data, response_data=None, error=None, elapsed=0):
        """Log API call for monitoring and debugging"""
        try:
            self.env['ringcentral.api.log'].sudo().create({
                'method': method.upper(),
                'endpoint': endpoint,
                'request_data': json.dumps(request_data, default=str)[:10000],
                'response_data': json.dumps(response_data, default=str)[:10000] if response_data else '',
                'error': error[:5000] if error else '',
                'elapsed_time': elapsed,
                'status': 'error' if error else 'success',
                'company_id': self.env.company.id,
                'user_id': self.env.user.id,
            })
        except Exception as e:
            _logger.error("Failed to log RingCentral API call: %s", str(e))
    
    @api.model
    def verify_webhook_signature(self, request_body, signature, signing_secret):
        """
        Verify RingCentral webhook signature
        
        :param request_body: Raw request body bytes
        :param signature: X-RingCentral-Signature header value
        :param signing_secret: Webhook signing secret
        :return: True if valid, False otherwise
        """
        if not signature or not signing_secret:
            return False
        
        expected_signature = hmac.new(
            signing_secret.encode('utf-8'),
            request_body,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    # ===========================
    # Voice API Methods
    # ===========================
    
    @api.model
    def ringout(self, from_number, to_number, caller_id=None, play_prompt=True, company=None):
        """
        Initiate a RingOut call (two-legged call)
        
        :param from_number: Caller's phone number (will ring first)
        :param to_number: Destination phone number
        :param caller_id: Caller ID to display (optional)
        :param play_prompt: Play connection prompt
        :return: RingOut session info
        """
        body = {
            'from': {'phoneNumber': from_number},
            'to': {'phoneNumber': to_number},
            'playPrompt': play_prompt,
        }
        if caller_id:
            body['callerId'] = {'phoneNumber': caller_id}
        
        return self._api_call('POST', '/restapi/v1.0/account/~/extension/~/ring-out', body=body, company=company)
    
    @api.model
    def ringout_status(self, ringout_id, company=None):
        """Get RingOut call status"""
        endpoint = f'/restapi/v1.0/account/~/extension/~/ring-out/{ringout_id}'
        return self._api_call('GET', endpoint, company=company)
    
    @api.model
    def ringout_cancel(self, ringout_id, company=None):
        """Cancel an in-progress RingOut call"""
        endpoint = f'/restapi/v1.0/account/~/extension/~/ring-out/{ringout_id}'
        return self._api_call('DELETE', endpoint, company=company)
    
    @api.model
    def get_call_log(self, params=None, company=None):
        """
        Get call log records
        
        :param params: Query parameters (dateFrom, dateTo, type, direction, etc.)
        :return: Call log records
        """
        default_params = {
            'view': 'Detailed',
            'perPage': 100,
        }
        if params:
            default_params.update(params)
        
        return self._api_call('GET', '/restapi/v1.0/account/~/extension/~/call-log', 
                              params=default_params, company=company)
    
    @api.model
    def get_active_calls(self, company=None):
        """Get active calls for the current extension"""
        return self._api_call('GET', '/restapi/v1.0/account/~/extension/~/active-calls', company=company)
    
    @api.model
    def get_call_recording(self, recording_id, company=None):
        """Download call recording content (binary-safe)."""
        company = company or self.env.company
        base_url = company.ringcentral_server_url or 'https://platform.ringcentral.com'
        endpoint = f'/restapi/v1.0/account/~/recording/{recording_id}/content'
        content_uri = f"{base_url}{endpoint}"
        return self.download_recording(content_uri, company=company)
    
    # ===========================
    # Call Control API Methods
    # ===========================
    
    @api.model
    def call_control_hold(self, telephony_session_id, party_id, company=None):
        """Put a call on hold"""
        endpoint = f'/restapi/v1.0/account/~/telephony/sessions/{telephony_session_id}/parties/{party_id}/hold'
        return self._api_call('POST', endpoint, company=company)
    
    @api.model
    def call_control_unhold(self, telephony_session_id, party_id, company=None):
        """Take a call off hold"""
        endpoint = f'/restapi/v1.0/account/~/telephony/sessions/{telephony_session_id}/parties/{party_id}/unhold'
        return self._api_call('POST', endpoint, company=company)
    
    @api.model
    def call_control_transfer(self, telephony_session_id, party_id, to_number, company=None):
        """Transfer a call to another number"""
        endpoint = f'/restapi/v1.0/account/~/telephony/sessions/{telephony_session_id}/parties/{party_id}/transfer'
        body = {'phoneNumber': to_number}
        return self._api_call('POST', endpoint, body=body, company=company)
    
    @api.model
    def call_control_mute(self, telephony_session_id, party_id, company=None):
        """Mute a call"""
        endpoint = f'/restapi/v1.0/account/~/telephony/sessions/{telephony_session_id}/parties/{party_id}/mute'
        return self._api_call('POST', endpoint, company=company)
    
    @api.model
    def call_control_unmute(self, telephony_session_id, party_id, company=None):
        """Unmute a call"""
        endpoint = f'/restapi/v1.0/account/~/telephony/sessions/{telephony_session_id}/parties/{party_id}/unmute'
        return self._api_call('POST', endpoint, company=company)
    
    @api.model
    def call_control_start_recording(self, telephony_session_id, party_id, company=None):
        """Start call recording"""
        endpoint = f'/restapi/v1.0/account/~/telephony/sessions/{telephony_session_id}/parties/{party_id}/recordings'
        return self._api_call('POST', endpoint, company=company)
    
    @api.model
    def call_control_stop_recording(self, telephony_session_id, party_id, recording_id, company=None):
        """Stop call recording"""
        endpoint = f'/restapi/v1.0/account/~/telephony/sessions/{telephony_session_id}/parties/{party_id}/recordings/{recording_id}'
        body = {'active': False}
        return self._api_call('PUT', endpoint, body=body, company=company)
    
    # ===========================
    # SMS/MMS API Methods
    # ===========================
    
    @api.model
    def send_sms(self, from_number, to_number, text, company=None):
        """
        Send an SMS message
        
        :param from_number: Sender's phone number
        :param to_number: Recipient's phone number (or list)
        :param text: Message text
        :return: Message info
        """
        # Normalize phone numbers
        from_number = self._normalize_phone_number(from_number)
        to_numbers = [to_number] if isinstance(to_number, str) else to_number
        to_numbers = [self._normalize_phone_number(n) for n in to_numbers]
        
        body = {
            'from': {'phoneNumber': from_number},
            'to': [{'phoneNumber': n} for n in to_numbers],
            'text': text,
        }
        return self._api_call('POST', '/restapi/v1.0/account/~/extension/~/sms', body=body, company=company)
    
    @api.model
    def send_mms(self, from_number, to_number, text, attachments, company=None):
        """
        Send an MMS message with attachments using multipart/form-data
        
        :param from_number: Sender's phone number
        :param to_number: Recipient's phone number (or list)
        :param text: Message text
        :param attachments: List of dicts with 'filename', 'content' (base64), 'content_type'
                           or list of (filename, content, content_type) tuples
        :return: Message info
        """
        # Normalize phone numbers
        from_number = self._normalize_phone_number(from_number)
        to_numbers = [to_number] if isinstance(to_number, str) else to_number
        to_numbers = [self._normalize_phone_number(n) for n in to_numbers]
        
        body = {
            'from': {'phoneNumber': from_number},
            'to': [{'phoneNumber': n} for n in to_numbers],
            'text': text or '',
        }
        
        # Convert attachments to proper format
        files = []
        for att in attachments:
            if isinstance(att, dict):
                files.append((
                    att.get('filename', 'attachment'),
                    att.get('content', ''),
                    att.get('content_type', 'application/octet-stream')
                ))
            elif isinstance(att, (list, tuple)) and len(att) >= 3:
                files.append((att[0], att[1], att[2]))
        
        if not files:
            raise UserError(_("MMS requires at least one attachment"))
        
        return self._api_call('POST', '/restapi/v1.0/account/~/extension/~/mms', 
                              body=body, files=files, company=company)
    
    @api.model
    def get_sms_messages(self, params=None, company=None):
        """Get SMS message history"""
        default_params = {
            'messageType': 'SMS',
            'perPage': 100,
        }
        if params:
            default_params.update(params)
        
        return self._api_call('GET', '/restapi/v1.0/account/~/extension/~/message-store', 
                              params=default_params, company=company)
    
    @api.model
    def get_voicemail_messages(self, params=None, company=None):
        """
        Get voicemail message history
        
        :param params: Optional query parameters (dateFrom, dateTo, perPage, etc.)
        :param company: Optional company context
        :return: Voicemail messages from message store
        """
        default_params = {
            'messageType': 'VoiceMail',
            'perPage': 100,
        }
        if params:
            default_params.update(params)
        
        response = self._api_call('GET', '/restapi/v1.0/account/~/extension/~/message-store', 
                                  params=default_params, company=company)
        
        # Return records list or empty list if no messages
        return response.get('records', []) if response else []
    
    # ===========================
    # Video/Meeting API Methods
    # ===========================
    
    @api.model
    def create_meeting(self, topic, start_time=None, duration=60, password=None, company=None):
        """
        Create a RingCentral Video meeting
        
        :param topic: Meeting topic/name
        :param start_time: Meeting start time (ISO format)
        :param duration: Meeting duration in minutes
        :param password: Meeting password (optional)
        :return: Meeting info with join URLs
        """
        body = {
            'topic': topic,
            'meetingType': 'Scheduled' if start_time else 'Instant',
            'schedule': {
                'startTime': start_time or datetime.utcnow().isoformat() + 'Z',
                'durationInMinutes': duration,
            },
        }
        if password:
            body['password'] = password
        
        return self._api_call('POST', '/restapi/v1.0/account/~/extension/~/meeting', body=body, company=company)
    
    @api.model
    def get_meeting(self, meeting_id, company=None):
        """Get meeting details"""
        endpoint = f'/restapi/v1.0/account/~/extension/~/meeting/{meeting_id}'
        return self._api_call('GET', endpoint, company=company)
    
    @api.model
    def delete_meeting(self, meeting_id, company=None):
        """Delete/cancel a meeting"""
        endpoint = f'/restapi/v1.0/account/~/extension/~/meeting/{meeting_id}'
        return self._api_call('DELETE', endpoint, company=company)
    
    @api.model
    def get_meeting_recordings(self, meeting_id, company=None):
        """Get meeting recordings"""
        endpoint = f'/restapi/v1.0/account/~/meeting/recordings'
        params = {'meetingId': meeting_id}
        return self._api_call('GET', endpoint, params=params, company=company)
    
    # ===========================
    # Presence API Methods
    # ===========================
    
    @api.model
    def get_presence(self, extension_id='~', company=None):
        """Get user presence status"""
        endpoint = f'/restapi/v1.0/account/~/extension/{extension_id}/presence'
        return self._api_call('GET', endpoint, company=company)
    
    @api.model
    def set_presence(self, presence_status, extension_id='~', company=None):
        """
        Set user presence status
        
        :param presence_status: Available, Busy, DoNotDisturb, Offline
        """
        endpoint = f'/restapi/v1.0/account/~/extension/{extension_id}/presence'
        body = {'userStatus': presence_status}
        return self._api_call('PUT', endpoint, body=body, company=company)
    
    # ===========================
    # Fax API Methods
    # ===========================
    
    @api.model
    def send_fax(self, to_number, documents, cover_page_text=None, resolution='High', company=None):
        """
        Send a fax with document attachments using multipart/form-data
        
        :param to_number: Recipient fax number (or list)
        :param documents: List of dicts with 'filename', 'content' (base64), 'content_type'
                         or list of (filename, content, content_type) tuples
                         Supported formats: PDF, TIFF, PNG, JPEG
        :param cover_page_text: Cover page text (optional)
        :param resolution: Fax resolution - 'High' or 'Low'
        :return: Fax message info
        """
        # Normalize phone numbers
        to_numbers = [to_number] if isinstance(to_number, str) else to_number
        to_numbers = [self._normalize_phone_number(n) for n in to_numbers]
        
        body = {
            'to': [{'phoneNumber': n} for n in to_numbers],
            'faxResolution': resolution,
        }
        if cover_page_text:
            body['coverPageText'] = cover_page_text
        
        # Convert documents to proper format
        files = []
        for doc in documents:
            if isinstance(doc, dict):
                files.append((
                    doc.get('filename', 'document.pdf'),
                    doc.get('content', ''),
                    doc.get('content_type', 'application/pdf')
                ))
            elif isinstance(doc, (list, tuple)) and len(doc) >= 3:
                files.append((doc[0], doc[1], doc[2]))
        
        if not files:
            raise UserError(_("Fax requires at least one document"))
        
        return self._api_call('POST', '/restapi/v1.0/account/~/extension/~/fax', 
                              body=body, files=files, company=company)
    
    @api.model
    def _normalize_phone_number(self, phone):
        """
        Normalize phone number to E.164 format
        
        :param phone: Phone number string
        :return: Normalized phone number
        """
        if not phone:
            return phone
        
        # Remove common formatting characters
        cleaned = ''.join(c for c in phone if c.isdigit() or c == '+')
        
        # If starts with +, keep as-is
        if cleaned.startswith('+'):
            return cleaned
        
        # If 10 digits (US), add +1 prefix
        if len(cleaned) == 10:
            return f'+1{cleaned}'
        
        # If 11 digits starting with 1 (US), add + prefix
        if len(cleaned) == 11 and cleaned.startswith('1'):
            return f'+{cleaned}'
        
        # Otherwise return as-is with + prefix
        return f'+{cleaned}'
    
    @api.model
    def get_fax_messages(self, params=None, company=None):
        """Get fax message history"""
        default_params = {
            'messageType': 'Fax',
            'perPage': 100,
        }
        if params:
            default_params.update(params)
        
        return self._api_call('GET', '/restapi/v1.0/account/~/extension/~/message-store', 
                              params=default_params, company=company)
    
    # ===========================
    # Subscription (Webhook) API Methods
    # ===========================
    
    @api.model
    def create_subscription(self, event_filters, delivery_url, company=None):
        """
        Create a webhook subscription for real-time events
        
        :param event_filters: List of event filter URIs
        :param delivery_url: Webhook delivery URL
        :return: Subscription info
        """
        body = {
            'eventFilters': event_filters,
            'deliveryMode': {
                'transportType': 'WebHook',
                'address': delivery_url,
            },
            'expiresIn': 604800,  # 7 days
        }
        return self._api_call('POST', '/restapi/v1.0/subscription', body=body, company=company)
    
    @api.model
    def renew_subscription(self, subscription_id, company=None):
        """Renew an existing subscription"""
        endpoint = f'/restapi/v1.0/subscription/{subscription_id}/renew'
        return self._api_call('POST', endpoint, company=company)
    
    @api.model
    def delete_subscription(self, subscription_id, company=None):
        """Delete a webhook subscription"""
        endpoint = f'/restapi/v1.0/subscription/{subscription_id}'
        return self._api_call('DELETE', endpoint, company=company)
    
    @api.model
    def get_subscriptions(self, company=None):
        """Get all active subscriptions"""
        return self._api_call('GET', '/restapi/v1.0/subscription', company=company)
    
    # ===========================
    # AI API Methods (RingSense)
    # ===========================
    
    @api.model
    def get_call_transcription(self, recording_id, company=None):
        """Get AI transcription for a call recording"""
        endpoint = f'/restapi/v1.0/account/~/extension/~/call-log/{recording_id}/transcription'
        return self._api_call('GET', endpoint, company=company)
    
    @api.model
    def analyze_call_sentiment(self, recording_id, company=None):
        """Get AI sentiment analysis for a call"""
        # Note: This uses RingSense AI API which may require separate enablement
        endpoint = f'/ai/v1/analyze'
        body = {
            'recordingId': recording_id,
            'features': ['sentiment', 'summary', 'topics', 'actionItems'],
        }
        return self._api_call('POST', endpoint, body=body, company=company)
    
    # ===========================
    # Account API Methods
    # ===========================
    
    @api.model
    def get_account_info(self, company=None):
        """Get account information"""
        return self._api_call('GET', '/restapi/v1.0/account/~', company=company)
    
    @api.model
    def get_extension_info(self, extension_id='~', company=None):
        """Get extension information"""
        endpoint = f'/restapi/v1.0/account/~/extension/{extension_id}'
        return self._api_call('GET', endpoint, company=company)
    
    @api.model
    def get_phone_numbers(self, company=None):
        """Get phone numbers associated with the account"""
        return self._api_call('GET', '/restapi/v1.0/account/~/extension/~/phone-number', company=company)
    
    # ===========================
    # Health Check Methods
    # ===========================
    
    @api.model
    def health_check(self, company=None):
        """
        Perform health check on RingCentral connection
        
        :return: Dict with status, latency, and details
        """
        result = {
            'status': 'unknown',
            'latency_ms': 0,
            'details': {},
            'timestamp': datetime.utcnow().isoformat(),
        }
        
        try:
            start = time.time()
            account_info = self.get_account_info(company)
            latency = (time.time() - start) * 1000
            
            result['status'] = 'healthy'
            result['latency_ms'] = round(latency, 2)
            result['details'] = {
                'account_id': account_info.get('id'),
                'account_status': account_info.get('status'),
                'service_plan': account_info.get('serviceInfo', {}).get('servicePlanName'),
            }
        except Exception as e:
            result['status'] = 'unhealthy'
            result['details'] = {'error': str(e)}
        
        return result
    
    @api.model
    def cron_health_check(self):
        """Scheduled health check for all companies with RingCentral configured"""
        companies = self.env['res.company'].search([
            ('ringcentral_client_id', '!=', False),
            ('ringcentral_enabled', '=', True),
        ])
        
        for company in companies:
            try:
                result = self.health_check(company)
                company.sudo().write({
                    'ringcentral_last_health_check': fields.Datetime.now(),
                    'ringcentral_health_status': result['status'],
                    'ringcentral_health_latency': result['latency_ms'],
                })
                
                if result['status'] != 'healthy':
                    _logger.warning(
                        "RingCentral health check failed for company %s: %s",
                        company.name, result['details']
                    )
            except Exception as e:
                _logger.error(
                    "RingCentral health check error for company %s: %s",
                    company.name, str(e)
                )
                company.sudo().write({
                    'ringcentral_last_health_check': fields.Datetime.now(),
                    'ringcentral_health_status': 'error',
                })
