# -*- coding: utf-8 -*-
"""
RingCentral Phone Number Model
==============================

Represents phone numbers (DIDs) synced from RingCentral.
Each number can be assigned to an extension and used as caller ID.

Industry Standard Implementation:
- Synced from RingCentral API /restapi/v1.0/account/~/phone-number
- Tracks usage type (Main, Direct, Toll-Free, etc.)
- Tracks features (CallerId, SmsSender, etc.)
- Supports per-app assignment for context-aware caller ID
"""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging
import json

_logger = logging.getLogger(__name__)


class RingCentralPhoneNumber(models.Model):
    """RingCentral Phone Number (DID) synchronized from RC account."""
    
    _name = 'ringcentral.phone.number'
    _description = 'RingCentral Phone Number'
    _order = 'is_primary desc, usage_type, phone_number'
    _rec_name = 'display_name'
    
    # ===========================
    # Core Fields
    # ===========================
    
    phone_number = fields.Char(
        string='Phone Number',
        required=True,
        index=True,
        help='Phone number in E.164 format (e.g., +14155551234)'
    )
    
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
    )
    
    formatted_number = fields.Char(
        string='Formatted Number',
        help='Human-readable formatted number'
    )
    
    rc_phone_id = fields.Char(
        string='RC Phone ID',
        index=True,
        help='RingCentral internal phone number ID'
    )
    
    # ===========================
    # Number Classification
    # ===========================
    
    usage_type = fields.Selection([
        ('MainCompanyNumber', 'Main Company Number'),
        ('AdditionalCompanyNumber', 'Additional Company Number'),
        ('DirectNumber', 'Direct Number'),
        ('CompanyNumber', 'Company Number'),
        ('CompanyFaxNumber', 'Company Fax Number'),
        ('ForwardedNumber', 'Forwarded Number'),
        ('ForwardedCompanyNumber', 'Forwarded Company Number'),
        ('BusinessMobileNumber', 'Business Mobile'),
        ('IntegrationNumber', 'Integration Number'),
        ('ContactCenterNumber', 'Contact Center Number'),
    ], string='Usage Type',
       default='DirectNumber',
       help='How this number is used in RingCentral')
    
    payment_type = fields.Selection([
        ('Local', 'Local'),
        ('TollFree', 'Toll-Free'),
        ('External', 'External'),
        ('Unknown', 'Unknown'),
    ], string='Payment Type',
       default='Local',
       help='Billing type for this number')
    
    type_field = fields.Selection([
        ('VoiceFax', 'Voice & Fax'),
        ('VoiceOnly', 'Voice Only'),
        ('FaxOnly', 'Fax Only'),
    ], string='Number Type',
       default='VoiceFax',
       help='Voice/Fax capability')
    
    # ===========================
    # Features (stored as JSON)
    # ===========================
    
    features_json = fields.Text(
        string='Features (JSON)',
        default='[]',
        help='JSON array of features enabled for this number'
    )
    
    can_be_caller_id = fields.Boolean(
        string='Can Be Caller ID',
        compute='_compute_features',
        store=True,
        help='This number can be used as outbound caller ID'
    )
    
    can_send_sms = fields.Boolean(
        string='Can Send SMS',
        compute='_compute_features',
        store=True,
        help='This number can be used to send SMS'
    )
    
    can_receive_sms = fields.Boolean(
        string='Can Receive SMS',
        compute='_compute_features',
        store=True,
        help='This number can receive SMS'
    )
    
    can_receive_fax = fields.Boolean(
        string='Can Receive Fax',
        compute='_compute_features',
        store=True,
        help='This number can receive faxes'
    )
    
    # ===========================
    # Relationships
    # ===========================
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        ondelete='cascade',
    )
    
    extension_id = fields.Many2one(
        'ringcentral.extension',
        string='Assigned Extension',
        ondelete='set null',
        help='Extension this number is assigned to'
    )
    
    # ===========================
    # App Assignment Flags
    # ===========================
    
    is_primary = fields.Boolean(
        string='Primary Number',
        default=False,
        help='Primary number for the assigned extension'
    )
    
    use_for_crm = fields.Boolean(
        string='Use for CRM/Leads',
        default=False,
        help='Use this number for outbound calls from CRM module'
    )
    
    use_for_sale = fields.Boolean(
        string='Use for Sales',
        default=False,
        help='Use this number for outbound calls from Sales module'
    )
    
    use_for_hr = fields.Boolean(
        string='Use for HR/Recruitment',
        default=False,
        help='Use this number for outbound calls from HR module'
    )
    
    use_for_helpdesk = fields.Boolean(
        string='Use for Support/Helpdesk',
        default=False,
        help='Use this number for outbound calls from Helpdesk module'
    )
    
    use_for_project = fields.Boolean(
        string='Use for Projects',
        default=False,
        help='Use this number for outbound calls from Project module'
    )
    
    use_for_general = fields.Boolean(
        string='Use for General',
        default=True,
        help='Use this number as fallback for all other contexts'
    )
    
    # ===========================
    # Sync Tracking
    # ===========================
    
    last_sync_date = fields.Datetime(
        string='Last Synced',
        help='Last time this number was synced from RingCentral'
    )
    
    # ===========================
    # Computed Methods
    # ===========================
    
    @api.depends('phone_number', 'formatted_number', 'usage_type', 'extension_id')
    def _compute_display_name(self):
        for num in self:
            display = num.formatted_number or num.phone_number or 'Unknown'
            if num.usage_type == 'MainCompanyNumber':
                display += ' (Main)'
            elif num.extension_id:
                display += f' ({num.extension_id.name})'
            num.display_name = display
    
    @api.depends('features_json')
    def _compute_features(self):
        for num in self:
            features = []
            try:
                if num.features_json:
                    features = json.loads(num.features_json)
            except (json.JSONDecodeError, TypeError):
                features = []
            
            num.can_be_caller_id = 'CallerId' in features
            num.can_send_sms = 'SmsSender' in features
            num.can_receive_sms = 'SmsReceiver' in features
            num.can_receive_fax = 'FaxReceiver' in features
    
    # ===========================
    # Constraints
    # ===========================
    
    _sql_constraints = [
        ('phone_number_company_unique',
         'UNIQUE(phone_number, company_id)',
         'Phone number must be unique per company.'),
    ]
    
    @api.constrains('phone_number')
    def _check_phone_number_format(self):
        """Validate phone number format (should be E.164)."""
        for record in self:
            if record.phone_number and not record.phone_number.startswith('+'):
                # Auto-fix: add + prefix if missing
                record.phone_number = '+' + record.phone_number.lstrip('+')
    
    # ===========================
    # Business Methods
    # ===========================
    
    def set_features(self, features_list):
        """Set features from a list."""
        self.ensure_one()
        self.features_json = json.dumps(features_list or [])
    
    def get_features(self):
        """Get features as a list."""
        self.ensure_one()
        try:
            return json.loads(self.features_json or '[]')
        except (json.JSONDecodeError, TypeError):
            return []
    
    @api.model
    def get_number_for_app(self, app_type, company=None, user=None):
        """
        Get the appropriate phone number for an app context.
        
        Priority order:
        1. User's personal default (if user has one and it matches app)
        2. App-specific number (use_for_crm, use_for_sale, etc.)
        3. General fallback number (use_for_general)
        4. Main company number
        
        :param app_type: One of 'crm', 'sale', 'hr', 'helpdesk', 'project', 'general'
        :param company: res.company record (defaults to current company)
        :param user: res.users record (defaults to current user)
        :return: ringcentral.phone.number record or False
        """
        company = company or self.env.company
        user = user or self.env.user
        
        domain = [
            ('company_id', '=', company.id),
            ('can_be_caller_id', '=', True),
        ]
        
        # Field mapping for app types
        app_field_map = {
            'crm': 'use_for_crm',
            'sale': 'use_for_sale',
            'hr': 'use_for_hr',
            'helpdesk': 'use_for_helpdesk',
            'project': 'use_for_project',
            'general': 'use_for_general',
        }
        
        # 1. Check user's personal default if they have an extension
        if hasattr(user, 'rc_multiline_ext_id') and user.rc_multiline_ext_id:
            user_numbers = self.search(domain + [
                ('extension_id', '=', user.rc_multiline_ext_id.id),
            ], order='is_primary desc', limit=1)
            if user_numbers:
                return user_numbers
        
        # 2. Check app-specific number
        app_field = app_field_map.get(app_type, 'use_for_general')
        app_numbers = self.search(domain + [
            (app_field, '=', True),
        ], order='is_primary desc', limit=1)
        if app_numbers:
            return app_numbers
        
        # 3. Fallback to general
        if app_type != 'general':
            general_numbers = self.search(domain + [
                ('use_for_general', '=', True),
            ], order='is_primary desc', limit=1)
            if general_numbers:
                return general_numbers
        
        # 4. Last resort: main company number
        main_numbers = self.search(domain + [
            ('usage_type', '=', 'MainCompanyNumber'),
        ], limit=1)
        if main_numbers:
            return main_numbers
        
        # 5. Any caller ID capable number
        any_number = self.search(domain, limit=1)
        return any_number or False
    
    def action_set_as_primary(self):
        """Set this number as primary for its extension."""
        self.ensure_one()
        if self.extension_id:
            # Clear other primaries for same extension
            self.search([
                ('extension_id', '=', self.extension_id.id),
                ('id', '!=', self.id),
            ]).write({'is_primary': False})
        self.is_primary = True
