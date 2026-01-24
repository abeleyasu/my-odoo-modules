# -*- coding: utf-8 -*-
"""
RingCentral Multi-line Controller
==================================

HTTP endpoints for context-aware phone number selection.
Provides the widget with the appropriate caller ID based on current context.

Industry Standard Implementation:
- RESTful JSON API endpoints
- Context detection from referrer/request
- Secure authentication via Odoo session
- Caching for performance
"""

from odoo import http, _
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)


class RingCentralMultilineController(http.Controller):
    """Controller for RingCentral multi-line widget integration."""
    
    # ===========================
    # App Type Detection
    # ===========================
    
    APP_TYPE_MAPPING = {
        '/web#action=': 'detect_from_action',
        'crm.lead': 'crm',
        'crm.opportunity': 'crm',
        'sale.order': 'sale',
        'sale.quotation': 'sale',
        'purchase.order': 'purchase',
        'hr.employee': 'hr',
        'hr.applicant': 'hr',
        'hr.recruitment': 'hr',
        'helpdesk.ticket': 'helpdesk',
        'project.project': 'project',
        'project.task': 'project',
        'account.move': 'account',
        'account.invoice': 'account',
        'res.partner': 'contacts',
        'calendar.event': 'calendar',
    }
    
    def _detect_app_type(self, model=None, referrer=None, action_id=None):
        """
        Detect the current Odoo app type from context.
        
        :param model: Model name (e.g., 'crm.lead')
        :param referrer: HTTP referrer URL
        :param action_id: Odoo action ID
        :return: App type string
        """
        # 1. Direct model mapping
        if model:
            for model_pattern, app_type in self.APP_TYPE_MAPPING.items():
                if model_pattern in model:
                    return app_type
        
        # 2. Check referrer URL for patterns
        if referrer:
            referrer_lower = referrer.lower()
            if 'crm' in referrer_lower or 'lead' in referrer_lower or 'opportunity' in referrer_lower:
                return 'crm'
            if 'sale' in referrer_lower or 'quotation' in referrer_lower:
                return 'sale'
            if 'purchase' in referrer_lower:
                return 'purchase'
            if 'hr' in referrer_lower or 'employee' in referrer_lower or 'recruitment' in referrer_lower:
                return 'hr'
            if 'helpdesk' in referrer_lower or 'ticket' in referrer_lower or 'support' in referrer_lower:
                return 'helpdesk'
            if 'project' in referrer_lower or 'task' in referrer_lower:
                return 'project'
            if 'account' in referrer_lower or 'invoice' in referrer_lower:
                return 'account'
        
        # 3. Check action if provided
        if action_id:
            try:
                action = request.env['ir.actions.act_window'].sudo().browse(int(action_id))
                if action.exists():
                    return self._detect_app_type(model=action.res_model)
            except (ValueError, TypeError):
                pass
        
        return 'general'
    
    # ===========================
    # Widget Configuration Endpoint
    # ===========================
    
    @http.route('/ringcentral/widget/contextual-config', type='json', auth='user', methods=['POST'])
    def get_contextual_config(self, **kwargs):
        """
        Get contextual widget configuration based on current app.
        
        Expected POST body:
        {
            "model": "crm.lead",
            "record_id": 123,
            "action_id": 456,
            "referrer": "http://..."
        }
        
        Returns:
        {
            "success": true,
            "config": {
                "fromNumber": "+14155551234",
                "formattedNumber": "(415) 555-1234",
                "enableFromNumberSetting": true,
                "availableNumbers": [...],
                "appType": "crm",
                "source": "app_config"
            }
        }
        """
        try:
            user = request.env.user
            company = user.company_id
            
            # Check if multi-line is enabled
            if not company.ringcentral_multiline_enabled:
                fallback_phone = getattr(company, 'ringcentral_fallback_number_id', False) or getattr(company, 'ringcentral_main_number_id', False)
                return {
                    'success': True,
                    'config': {
                        'fromNumber': fallback_phone.phone_number if fallback_phone else None,
                        'formattedNumber': fallback_phone.formatted_number if fallback_phone else None,
                        'enableFromNumberSetting': False,
                        'appType': 'general',
                        'source': 'company_default',
                    }
                }
            
            # Extract context from request
            model = kwargs.get('model')
            record_id = kwargs.get('record_id')
            action_id = kwargs.get('action_id')
            referrer = kwargs.get('referrer') or request.httprequest.referrer
            
            # Detect app type
            app_type = self._detect_app_type(model=model, referrer=referrer, action_id=action_id)

            # If company disabled context-aware routing, force general.
            if hasattr(company, 'ringcentral_context_aware_routing') and not company.ringcentral_context_aware_routing:
                app_type = 'general'
            
            # Get phone number configuration
            AppConfig = request.env['ringcentral.app.config']
            result = AppConfig.get_phone_number_for_context({
                'app_type': app_type,
                'user_id': user.id,
                'company_id': company.id,
                'model': model,
                'record_id': record_id,
            })
            
            # Get available numbers for user
            available_numbers = []
            if company.ringcentral_allow_user_caller_id and user.ringcentral_can_change_caller_id:
                for num in user.get_available_caller_ids():
                    available_numbers.append({
                        'phoneNumber': num['phone_number'],
                        'formattedNumber': num['formatted_number'],
                        'label': num['label'],
                    })
            
            return {
                'success': True,
                'config': {
                    'fromNumber': result.get('phone_number'),
                    'formattedNumber': result.get('formatted_number'),
                    'extensionId': result.get('extension_id'),
                    'enableFromNumberSetting': company.ringcentral_enable_from_number_setting and user.ringcentral_can_change_caller_id,
                    'availableNumbers': available_numbers,
                    'appType': app_type,
                    'source': result.get('source'),
                }
            }
            
        except Exception as e:
            _logger.error(f"Error getting contextual config: {e}")
            return {
                'success': False,
                'error': str(e),
            }
    
    @http.route('/ringcentral/widget/update-caller-id', type='json', auth='user', methods=['POST'])
    def update_caller_id(self, **kwargs):
        """
        Update user's selected caller ID preference.
        
        Expected POST body:
        {
            "phone_number": "+14155551234"
        }
        """
        try:
            user = request.env.user
            phone_number = kwargs.get('phone_number')
            
            if not phone_number:
                return {'success': False, 'error': 'Phone number required'}
            
            # Find the phone number record
            PhoneNumber = request.env['ringcentral.phone.number']
            phone = PhoneNumber.search([
                ('phone_number', '=', phone_number),
                ('company_id', '=', user.company_id.id),
                ('can_be_caller_id', '=', True),
            ], limit=1)
            
            if not phone:
                return {'success': False, 'error': 'Phone number not found or not available'}
            
            # Check if user has access to this number
            if phone.id not in [n['id'] for n in user.get_available_caller_ids()]:
                return {'success': False, 'error': 'Not authorized to use this phone number'}
            
            # Update user preference
            user.ringcentral_default_from_number_id = phone.id
            
            return {
                'success': True,
                'phoneNumber': phone.phone_number,
                'formattedNumber': phone.formatted_number,
            }
            
        except Exception as e:
            _logger.error(f"Error updating caller ID: {e}")
            return {'success': False, 'error': str(e)}
    
    # ===========================
    # Data Endpoints
    # ===========================
    
    @http.route('/ringcentral/extensions', type='json', auth='user', methods=['GET', 'POST'])
    def get_extensions(self, **kwargs):
        """Get all extensions for current company."""
        try:
            company = request.env.user.company_id
            extensions = request.env['ringcentral.extension'].search([
                ('company_id', '=', company.id),
            ])
            
            return {
                'success': True,
                'extensions': [{
                    'id': ext.id,
                    'name': ext.name,
                    'extensionNumber': ext.extension_number,
                    'type': ext.extension_type,
                    'status': ext.status,
                    'email': ext.email,
                } for ext in extensions]
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @http.route('/ringcentral/phone-numbers', type='json', auth='user', methods=['GET', 'POST'])
    def get_phone_numbers(self, **kwargs):
        """Get all phone numbers for current company."""
        try:
            company = request.env.user.company_id
            only_caller_id = kwargs.get('only_caller_id', False)
            
            domain = [('company_id', '=', company.id)]
            if only_caller_id:
                domain.append(('can_be_caller_id', '=', True))
            
            numbers = request.env['ringcentral.phone.number'].search(domain)
            
            return {
                'success': True,
                'phoneNumbers': [{
                    'id': num.id,
                    'phoneNumber': num.phone_number,
                    'formattedNumber': num.formatted_number,
                    'usageType': num.usage_type,
                    'canBeCallerId': num.can_be_caller_id,
                    'canSendSms': num.can_send_sms,
                    'extensionId': num.extension_id.id if num.extension_id else None,
                } for num in numbers]
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @http.route('/ringcentral/call-queues', type='json', auth='user', methods=['GET', 'POST'])
    def get_call_queues(self, **kwargs):
        """Get all call queues for current company."""
        try:
            company = request.env.user.company_id
            queues = request.env['ringcentral.call.queue'].search([
                ('company_id', '=', company.id),
            ])
            
            return {
                'success': True,
                'callQueues': [{
                    'id': queue.id,
                    'name': queue.name,
                    'extensionNumber': queue.extension_number,
                    'routingType': queue.routing_type,
                    'memberCount': queue.member_count,
                    'departmentId': queue.department_id.id if queue.department_id else None,
                    'departmentName': queue.department_id.name if queue.department_id else None,
                } for queue in queues]
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @http.route('/ringcentral/app-configs', type='json', auth='user', methods=['GET', 'POST'])
    def get_app_configs(self, **kwargs):
        """Get all app configurations for current company."""
        try:
            company = request.env.user.company_id
            configs = request.env['ringcentral.app.config'].search([
                ('company_id', '=', company.id),
                ('active', '=', True),
            ])
            
            return {
                'success': True,
                'appConfigs': [{
                    'id': config.id,
                    'appType': config.app_type,
                    'phoneNumber': config.phone_number,
                    'formattedPhone': config.formatted_phone,
                    'smsEnabled': config.sms_enabled,
                    'allowUserOverride': config.allow_user_override,
                } for config in configs]
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # ===========================
    # Sync Endpoints
    # ===========================
    
    @http.route('/ringcentral/sync', type='json', auth='user', methods=['POST'])
    def trigger_sync(self, **kwargs):
        """Trigger a full RingCentral data sync (admin only)."""
        try:
            user = request.env.user
            
            # Check admin permission
            if not user.has_group('ringcentral_multiline.group_ringcentral_manager'):
                return {'success': False, 'error': 'Admin permission required'}
            
            company = user.company_id
            SyncService = request.env['ringcentral.sync.service']
            results = SyncService.sync_all(company)
            
            return {
                'success': True,
                'results': {
                    'extensions': results['extensions'],
                    'phoneNumbers': results['phone_numbers'],
                    'callQueues': results['call_queues'],
                    'totalTimeSeconds': results['total_time_seconds'],
                }
            }
        except Exception as e:
            _logger.error(f"Sync failed: {e}")
            return {'success': False, 'error': str(e)}
