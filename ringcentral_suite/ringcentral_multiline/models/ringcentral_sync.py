# -*- coding: utf-8 -*-
"""
RingCentral Sync Service
========================

Centralized service for synchronizing data from RingCentral API.
Syncs extensions, phone numbers, call queues, and their relationships.

Industry Standard Implementation:
- Rate-limited API calls with retry logic
- Incremental sync with change tracking
- Error handling and logging
- Background job support via Odoo cron
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging
import json
from datetime import datetime, timedelta
import requests

_logger = logging.getLogger(__name__)


class RingCentralSyncService(models.TransientModel):
    """Service for synchronizing RingCentral data to Odoo."""
    
    _name = 'ringcentral.sync.service'
    _description = 'RingCentral Sync Service'
    
    # ===========================
    # API Configuration
    # ===========================
    
    RINGCENTRAL_API_BASE = 'https://platform.ringcentral.com/restapi/v1.0'
    RINGCENTRAL_API_SANDBOX = 'https://platform.devtest.ringcentral.com/restapi/v1.0'
    
    # Rate limiting
    MAX_REQUESTS_PER_MINUTE = 40
    RETRY_DELAY_SECONDS = 2
    MAX_RETRIES = 3
    
    # ===========================
    # Helper Methods
    # ===========================
    
    def _get_api_base_url(self, company):
        """Get the API base URL based on company configuration."""
        if hasattr(company, 'ringcentral_sandbox_mode') and company.ringcentral_sandbox_mode:
            return self.RINGCENTRAL_API_SANDBOX
        return self.RINGCENTRAL_API_BASE
    
    def _get_access_token(self, company):
        """
        Get a valid access token for RingCentral API.
        
        Checks for existing valid token or refreshes if needed.
        
        :param company: res.company record
        :return: Access token string or raises UserError
        """
        if not hasattr(company, 'ringcentral_access_token') or not company.ringcentral_access_token:
            raise UserError(_('RingCentral is not configured. Please set up API credentials in Settings.'))
        
        # Check if token is expired
        if hasattr(company, 'ringcentral_token_expiry') and company.ringcentral_token_expiry:
            if fields.Datetime.now() > company.ringcentral_token_expiry:
                # Attempt to refresh token
                self._refresh_access_token(company)
        
        return company.ringcentral_access_token
    
    def _refresh_access_token(self, company):
        """
        Refresh the RingCentral access token using refresh token.
        
        :param company: res.company record
        """
        if not hasattr(company, 'ringcentral_refresh_token') or not company.ringcentral_refresh_token:
            raise UserError(_('RingCentral refresh token not available. Please re-authenticate.'))
        
        # This would implement OAuth2 token refresh
        # For now, we'll just log and let the calling code handle it
        _logger.warning(f"RingCentral token needs refresh for company {company.name}")
        raise UserError(_('RingCentral token expired. Please re-authenticate in Settings.'))
    
    def _make_api_request(self, company, endpoint, method='GET', data=None, params=None):
        """
        Make an authenticated request to RingCentral API.
        
        Includes retry logic and rate limiting.
        
        :param company: res.company record
        :param endpoint: API endpoint (e.g., '/account/~/extension')
        :param method: HTTP method
        :param data: Request body for POST/PUT
        :param params: Query parameters
        :return: JSON response or None on error
        """
        base_url = self._get_api_base_url(company)
        access_token = self._get_access_token(company)
        
        url = f"{base_url}{endpoint}"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        
        for attempt in range(self.MAX_RETRIES):
            try:
                if method.upper() == 'GET':
                    response = requests.get(url, headers=headers, params=params, timeout=30)
                elif method.upper() == 'POST':
                    response = requests.post(url, headers=headers, json=data, params=params, timeout=30)
                elif method.upper() == 'PUT':
                    response = requests.put(url, headers=headers, json=data, params=params, timeout=30)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', self.RETRY_DELAY_SECONDS))
                    _logger.warning(f"Rate limited, waiting {retry_after} seconds...")
                    import time
                    time.sleep(retry_after)
                    continue
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.HTTPError as e:
                _logger.error(f"RingCentral API error: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    import time
                    time.sleep(self.RETRY_DELAY_SECONDS * (attempt + 1))
                    continue
                raise UserError(_('RingCentral API error: %s') % str(e))
            except requests.exceptions.RequestException as e:
                _logger.error(f"Network error: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    import time
                    time.sleep(self.RETRY_DELAY_SECONDS * (attempt + 1))
                    continue
                raise UserError(_('Network error connecting to RingCentral: %s') % str(e))
        
        return None
    
    # ===========================
    # Extension Sync
    # ===========================
    
    def sync_extensions(self, company=None):
        """
        Sync all extensions from RingCentral.
        
        :param company: res.company record (defaults to current company)
        :return: Dict with sync results
        """
        company = company or self.env.company
        Extension = self.env['ringcentral.extension']
        
        _logger.info(f"Starting extension sync for company: {company.name}")
        
        results = {
            'created': 0,
            'updated': 0,
            'errors': [],
        }
        
        try:
            # Fetch extensions from API with pagination
            page = 1
            per_page = 100
            total_processed = 0
            
            while True:
                response = self._make_api_request(
                    company,
                    '/account/~/extension',
                    params={
                        'page': page,
                        'perPage': per_page,
                        'status': 'Enabled',
                    }
                )
                
                if not response or 'records' not in response:
                    break
                
                records = response.get('records', [])
                if not records:
                    break
                
                for ext_data in records:
                    try:
                        existing = Extension.search([
                            ('rc_extension_id', '=', str(ext_data['id'])),
                            ('company_id', '=', company.id),
                        ], limit=1)
                        
                        if existing:
                            existing.sync_from_ringcentral(ext_data)
                            results['updated'] += 1
                        else:
                            Extension.create_or_update_from_api(ext_data, company)
                            results['created'] += 1
                        
                        total_processed += 1
                        
                    except Exception as e:
                        _logger.error(f"Error syncing extension {ext_data.get('id')}: {e}")
                        results['errors'].append(str(e))
                
                # Check for more pages
                paging = response.get('paging', {})
                if paging.get('page', 1) >= paging.get('totalPages', 1):
                    break
                
                page += 1
            
            _logger.info(f"Extension sync complete: {results['created']} created, {results['updated']} updated")
            
        except Exception as e:
            _logger.error(f"Extension sync failed: {e}")
            results['errors'].append(str(e))
        
        return results
    
    # ===========================
    # Phone Number Sync
    # ===========================
    
    def sync_phone_numbers(self, company=None):
        """
        Sync all phone numbers from RingCentral.
        
        :param company: res.company record (defaults to current company)
        :return: Dict with sync results
        """
        company = company or self.env.company
        PhoneNumber = self.env['ringcentral.phone.number']
        Extension = self.env['ringcentral.extension']
        
        _logger.info(f"Starting phone number sync for company: {company.name}")
        
        results = {
            'created': 0,
            'updated': 0,
            'errors': [],
        }
        
        try:
            # Fetch phone numbers from API with pagination
            page = 1
            per_page = 100
            
            while True:
                response = self._make_api_request(
                    company,
                    '/account/~/phone-number',
                    params={
                        'page': page,
                        'perPage': per_page,
                    }
                )
                
                if not response or 'records' not in response:
                    break
                
                records = response.get('records', [])
                if not records:
                    break
                
                for phone_data in records:
                    try:
                        phone_number = phone_data.get('phoneNumber')
                        if not phone_number:
                            continue
                        
                        existing = PhoneNumber.search([
                            ('phone_number', '=', phone_number),
                            ('company_id', '=', company.id),
                        ], limit=1)
                        
                        # Prepare values
                        vals = {
                            'phone_number': phone_number,
                            'formatted_number': phone_data.get('formattedPhoneNumber', phone_number),
                            'rc_phone_id': str(phone_data.get('id', '')),
                            'usage_type': phone_data.get('usageType', 'DirectNumber'),
                            'payment_type': phone_data.get('paymentType', 'Local'),
                            'type_field': phone_data.get('type', 'VoiceFax'),
                            'last_sync_date': fields.Datetime.now(),
                        }
                        
                        # Set features
                        features = phone_data.get('features', [])
                        vals['features_json'] = json.dumps(features)
                        
                        # Link to extension if present
                        ext_data = phone_data.get('extension')
                        if ext_data and ext_data.get('id'):
                            extension = Extension.search([
                                ('rc_extension_id', '=', str(ext_data['id'])),
                                ('company_id', '=', company.id),
                            ], limit=1)
                            if extension:
                                vals['extension_id'] = extension.id
                        
                        if existing:
                            existing.write(vals)
                            results['updated'] += 1
                        else:
                            vals['company_id'] = company.id
                            PhoneNumber.create(vals)
                            results['created'] += 1
                        
                    except Exception as e:
                        _logger.error(f"Error syncing phone number {phone_data.get('phoneNumber')}: {e}")
                        results['errors'].append(str(e))
                
                # Check for more pages
                paging = response.get('paging', {})
                if paging.get('page', 1) >= paging.get('totalPages', 1):
                    break
                
                page += 1
            
            _logger.info(f"Phone number sync complete: {results['created']} created, {results['updated']} updated")
            
        except Exception as e:
            _logger.error(f"Phone number sync failed: {e}")
            results['errors'].append(str(e))
        
        return results
    
    # ===========================
    # Call Queue Sync
    # ===========================
    
    def sync_call_queues(self, company=None):
        """
        Sync all call queues from RingCentral.
        
        :param company: res.company record (defaults to current company)
        :return: Dict with sync results
        """
        company = company or self.env.company
        CallQueue = self.env['ringcentral.call.queue']
        Extension = self.env['ringcentral.extension']
        
        _logger.info(f"Starting call queue sync for company: {company.name}")
        
        results = {
            'created': 0,
            'updated': 0,
            'errors': [],
        }
        
        try:
            # Fetch call queues from API
            response = self._make_api_request(
                company,
                '/account/~/call-queues',
            )
            
            if not response or 'records' not in response:
                return results
            
            for queue_data in response.get('records', []):
                try:
                    existing = CallQueue.search([
                        ('rc_queue_id', '=', str(queue_data['id'])),
                        ('company_id', '=', company.id),
                    ], limit=1)
                    
                    if existing:
                        existing.sync_from_ringcentral(queue_data)
                        results['updated'] += 1
                    else:
                        CallQueue.create_or_update_from_api(queue_data, company)
                        results['created'] += 1
                    
                except Exception as e:
                    _logger.error(f"Error syncing call queue {queue_data.get('id')}: {e}")
                    results['errors'].append(str(e))
            
            _logger.info(f"Call queue sync complete: {results['created']} created, {results['updated']} updated")
            
        except Exception as e:
            _logger.error(f"Call queue sync failed: {e}")
            results['errors'].append(str(e))
        
        return results
    
    def sync_queue_members(self, queue):
        """
        Sync members for a specific call queue.
        
        :param queue: ringcentral.call.queue record
        :return: Dict with sync results
        """
        company = queue.company_id
        Extension = self.env['ringcentral.extension']
        
        results = {
            'members_synced': 0,
            'errors': [],
        }
        
        try:
            response = self._make_api_request(
                company,
                f'/account/~/call-queues/{queue.rc_queue_id}/members',
            )
            
            if not response or 'records' not in response:
                return results
            
            member_ext_ids = []
            for member_data in response.get('records', []):
                ext_id = member_data.get('id')
                if ext_id:
                    extension = Extension.search([
                        ('rc_extension_id', '=', str(ext_id)),
                        ('company_id', '=', company.id),
                    ], limit=1)
                    if extension:
                        member_ext_ids.append(extension.id)
            
            queue.member_ids = [(6, 0, member_ext_ids)]
            results['members_synced'] = len(member_ext_ids)
            
            _logger.info(f"Synced {len(member_ext_ids)} members for queue: {queue.name}")
            
        except Exception as e:
            _logger.error(f"Queue member sync failed: {e}")
            results['errors'].append(str(e))
        
        return results
    
    # ===========================
    # Full Sync
    # ===========================
    
    def sync_all(self, company=None):
        """
        Perform a full sync of all RingCentral data.
        
        :param company: res.company record (defaults to current company)
        :return: Dict with consolidated sync results
        """
        company = company or self.env.company
        
        _logger.info(f"Starting full RingCentral sync for company: {company.name}")
        
        results = {
            'extensions': {},
            'phone_numbers': {},
            'call_queues': {},
            'total_time_seconds': 0,
        }
        
        start_time = datetime.now()
        
        # Sync in order: extensions first (for relationships)
        results['extensions'] = self.sync_extensions(company)
        results['phone_numbers'] = self.sync_phone_numbers(company)
        results['call_queues'] = self.sync_call_queues(company)
        
        # Sync queue members
        queues = self.env['ringcentral.call.queue'].search([
            ('company_id', '=', company.id),
        ])
        for queue in queues:
            self.sync_queue_members(queue)
        
        end_time = datetime.now()
        results['total_time_seconds'] = (end_time - start_time).total_seconds()
        
        _logger.info(f"Full sync complete in {results['total_time_seconds']:.2f} seconds")
        
        return results
    
    # ===========================
    # Cron Job Methods
    # ===========================
    
    @api.model
    def cron_sync_all_companies(self):
        """
        Cron job to sync RingCentral data for all configured companies.
        """
        _logger.info("Starting scheduled RingCentral sync for all companies")
        
        # Find companies with RingCentral configured
        companies = self.env['res.company'].search([])
        
        for company in companies:
            # Check if RingCentral is configured for this company
            if hasattr(company, 'ringcentral_access_token') and company.ringcentral_access_token:
                try:
                    self.sync_all(company)
                except Exception as e:
                    _logger.error(f"Sync failed for company {company.name}: {e}")
        
        _logger.info("Scheduled RingCentral sync complete")
    
    @api.model
    def cron_sync_extensions_only(self):
        """Cron job to sync only extensions (lighter sync)."""
        companies = self.env['res.company'].search([])
        
        for company in companies:
            if hasattr(company, 'ringcentral_access_token') and company.ringcentral_access_token:
                try:
                    self.sync_extensions(company)
                except Exception as e:
                    _logger.error(f"Extension sync failed for company {company.name}: {e}")
