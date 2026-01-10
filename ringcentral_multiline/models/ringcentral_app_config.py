# -*- coding: utf-8 -*-
"""
RingCentral App Configuration Model
===================================

Defines per-application phone number configuration.
Allows different Odoo apps (CRM, Sales, HR, etc.) to use different phone numbers.

Industry Standard Implementation:
- Each app type gets its own caller ID configuration
- Priority-based fallback system
- Supports both company-wide and per-user overrides
"""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class RingCentralAppConfig(models.Model):
    """Per-application RingCentral phone number configuration."""
    
    _name = 'ringcentral.app.config'
    _description = 'RingCentral App Configuration'
    _order = 'sequence, app_type'
    _rec_name = 'display_name'
    
    # ===========================
    # Core Fields
    # ===========================
    
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Order for displaying configurations'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Inactive configurations are ignored'
    )
    
    # ===========================
    # Application Type
    # ===========================
    
    app_type = fields.Selection([
        ('crm', 'CRM / Leads'),
        ('sale', 'Sales / Quotations'),
        ('purchase', 'Purchase'),
        ('hr', 'HR / Recruitment'),
        ('helpdesk', 'Helpdesk / Support'),
        ('project', 'Project'),
        ('account', 'Accounting / Invoicing'),
        ('contacts', 'Contacts'),
        ('calendar', 'Calendar'),
        ('general', 'General / Default'),
    ], string='Application',
       required=True,
       help='Which Odoo application this configuration applies to')
    
    app_icon = fields.Char(
        string='App Icon',
        compute='_compute_app_icon',
        help='Font Awesome icon for this app'
    )
    
    description = fields.Text(
        string='Description',
        help='Additional notes about this configuration'
    )
    
    # ===========================
    # Phone Number Configuration
    # ===========================
    
    phone_number_id = fields.Many2one(
        'ringcentral.phone.number',
        string='Outbound Caller ID',
        required=True,
        ondelete='restrict',
        domain="[('can_be_caller_id', '=', True), ('company_id', '=', company_id)]",
        help='Phone number to use as caller ID for this application'
    )
    
    phone_number = fields.Char(
        related='phone_number_id.phone_number',
        string='Phone Number',
        readonly=True,
    )
    
    formatted_phone = fields.Char(
        related='phone_number_id.formatted_number',
        string='Formatted Phone',
        readonly=True,
    )
    
    # ===========================
    # Fallback Configuration
    # ===========================
    
    fallback_to_general = fields.Boolean(
        string='Fallback to General',
        default=True,
        help='If phone number unavailable, use general configuration'
    )
    
    fallback_phone_number_id = fields.Many2one(
        'ringcentral.phone.number',
        string='Fallback Number',
        ondelete='set null',
        domain="[('can_be_caller_id', '=', True), ('company_id', '=', company_id)]",
        help='Alternative number if primary is unavailable'
    )
    
    # ===========================
    # SMS Configuration
    # ===========================
    
    sms_enabled = fields.Boolean(
        string='SMS Enabled',
        default=True,
        help='Enable SMS capabilities for this app'
    )
    
    sms_phone_number_id = fields.Many2one(
        'ringcentral.phone.number',
        string='SMS Phone Number',
        ondelete='set null',
        domain="[('can_send_sms', '=', True), ('company_id', '=', company_id)]",
        help='Phone number to use for SMS in this app (if different from voice)'
    )
    
    # ===========================
    # Call Queue Association
    # ===========================
    
    call_queue_id = fields.Many2one(
        'ringcentral.call.queue',
        string='Associated Call Queue',
        ondelete='set null',
        domain="[('company_id', '=', company_id)]",
        help='Call queue associated with this app for inbound routing'
    )
    
    # ===========================
    # User Override Settings
    # ===========================
    
    allow_user_override = fields.Boolean(
        string='Allow User Override',
        default=True,
        help='Users can override this with their personal number'
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
    
    # ===========================
    # Computed Methods
    # ===========================
    
    @api.depends('app_type', 'phone_number_id')
    def _compute_display_name(self):
        app_labels = dict(self._fields['app_type'].selection)
        for config in self:
            app_name = app_labels.get(config.app_type, config.app_type or 'Unknown')
            phone = config.phone_number_id.formatted_number or config.phone_number_id.phone_number or 'No Number'
            config.display_name = f"{app_name}: {phone}"
    
    @api.depends('app_type')
    def _compute_app_icon(self):
        icon_map = {
            'crm': 'fa-bullhorn',
            'sale': 'fa-shopping-cart',
            'purchase': 'fa-truck',
            'hr': 'fa-users',
            'helpdesk': 'fa-life-ring',
            'project': 'fa-tasks',
            'account': 'fa-money',
            'contacts': 'fa-address-book',
            'calendar': 'fa-calendar',
            'general': 'fa-phone',
        }
        for config in self:
            config.app_icon = icon_map.get(config.app_type, 'fa-phone')
    
    # ===========================
    # Constraints
    # ===========================
    
    _sql_constraints = [
        ('app_type_company_unique',
         'UNIQUE(app_type, company_id)',
         'Only one configuration per app type per company is allowed.'),
    ]
    
    @api.constrains('phone_number_id')
    def _check_phone_number_caller_id(self):
        """Ensure the selected number can be used as caller ID."""
        for config in self:
            if config.phone_number_id and not config.phone_number_id.can_be_caller_id:
                raise ValidationError(_(
                    "The selected phone number %s cannot be used as Caller ID. "
                    "Please select a number with Caller ID capability."
                ) % config.phone_number_id.phone_number)
    
    # ===========================
    # Business Methods
    # ===========================
    
    @api.model
    def get_config_for_app(self, app_type, company=None):
        """
        Get the configuration for a specific app type.
        
        :param app_type: One of the app_type selection values
        :param company: res.company record (defaults to current company)
        :return: ringcentral.app.config record or False
        """
        company = company or self.env.company
        
        config = self.search([
            ('app_type', '=', app_type),
            ('company_id', '=', company.id),
            ('active', '=', True),
        ], limit=1)
        
        # Fallback to general if not found
        if not config and app_type != 'general':
            config = self.search([
                ('app_type', '=', 'general'),
                ('company_id', '=', company.id),
                ('active', '=', True),
            ], limit=1)
        
        return config or False
    
    @api.model
    def get_phone_number_for_context(self, context_info):
        """
        Get the appropriate phone number based on context.
        
        :param context_info: Dict with keys:
            - app_type: string (crm, sale, hr, etc.)
            - user_id: int (optional)
            - company_id: int (optional)
            - model: string (optional, e.g., 'crm.lead')
            - record_id: int (optional)
        :return: Dict with phone_number, formatted_number, extension_id
        """
        app_type = context_info.get('app_type', 'general')
        user_id = context_info.get('user_id') or self.env.uid
        company_id = context_info.get('company_id') or self.env.company.id
        
        user = self.env['res.users'].browse(user_id)
        company = self.env['res.company'].browse(company_id)
        
        result = {
            'phone_number': None,
            'formatted_number': None,
            'extension_id': None,
            'source': None,
        }

        def _set_from_phone(phone, source):
            result.update({
                'phone_number': phone.phone_number,
                'formatted_number': phone.formatted_number or phone.phone_number,
                'extension_id': phone.extension_id.rc_extension_id if phone.extension_id else None,
                'source': source,
            })
            return result

        # If context-aware routing is disabled at company level, treat all contexts as "general".
        if hasattr(company, 'ringcentral_context_aware_routing') and not company.ringcentral_context_aware_routing:
            app_type = 'general'
        
        config = self.get_config_for_app(app_type, company)

        # 0) Forced personal caller ID (explicit user preference)
        if (
            hasattr(company, 'ringcentral_allow_user_caller_id')
            and company.ringcentral_allow_user_caller_id
            and hasattr(user, 'ringcentral_use_personal_number')
            and user.ringcentral_use_personal_number
            and hasattr(user, 'ringcentral_default_from_number_id')
            and user.ringcentral_default_from_number_id
            and user.ringcentral_default_from_number_id.can_be_caller_id
        ):
            return _set_from_phone(user.ringcentral_default_from_number_id, 'user_personal_forced')

        # 1) User override (if allowed by company + app config)
        if (
            config
            and config.allow_user_override
            and hasattr(company, 'ringcentral_allow_user_caller_id')
            and company.ringcentral_allow_user_caller_id
            and hasattr(user, 'ringcentral_default_from_number_id')
            and user.ringcentral_default_from_number_id
            and user.ringcentral_default_from_number_id.can_be_caller_id
        ):
            return _set_from_phone(user.ringcentral_default_from_number_id, 'user_override')

        # 2) Department outbound override (if configured)
        try:
            Employee = self.env['hr.employee'].sudo()
            employee = Employee.search([
                ('user_id', '=', user.id),
                ('company_id', '=', company.id),
            ], limit=1)
            department = employee.department_id if employee else False
            if (
                department
                and getattr(department, 'ringcentral_routing_enabled', False)
                and getattr(department, 'ringcentral_use_queue_for_outbound', False)
            ):
                dept_number = department.get_department_caller_id()
                if dept_number:
                    phone = self.env['ringcentral.phone.number'].search([
                        ('company_id', '=', company.id),
                        ('phone_number', '=', dept_number),
                        ('can_be_caller_id', '=', True),
                    ], limit=1)
                    if phone:
                        return _set_from_phone(phone, 'department')
                    # If we can't find a matching phone record, still return the number.
                    result.update({
                        'phone_number': dept_number,
                        'formatted_number': dept_number,
                        'extension_id': None,
                        'source': 'department',
                    })
                    return result
        except Exception as e:
            _logger.debug(f"Department caller ID lookup skipped/failed: {e}")
        
        # 3) Use app configuration (with fallback handling)
        if config and config.phone_number_id and config.phone_number_id.can_be_caller_id:
            return _set_from_phone(config.phone_number_id, 'app_config')

        # App-level fallback (explicit fallback number)
        if config and config.fallback_phone_number_id and config.fallback_phone_number_id.can_be_caller_id:
            return _set_from_phone(config.fallback_phone_number_id, 'app_fallback')

        # App-level fallback to general
        if config and config.fallback_to_general and app_type != 'general':
            general_config = self.get_config_for_app('general', company)
            if general_config and general_config.phone_number_id and general_config.phone_number_id.can_be_caller_id:
                return _set_from_phone(general_config.phone_number_id, 'general_fallback')
        
        # 4) Fallback to phone number model method (legacy per-app flags)
        phone = self.env['ringcentral.phone.number'].get_number_for_app(app_type, company, user)
        if phone:
            return _set_from_phone(phone, 'fallback')

        # 5) Company-level fallback numbers
        company_fallback = getattr(company, 'ringcentral_fallback_number_id', False) or getattr(company, 'ringcentral_main_number_id', False)
        if company_fallback and company_fallback.can_be_caller_id:
            return _set_from_phone(company_fallback, 'company_fallback')
        
        return result
    
    def action_test_configuration(self):
        """Test the configuration by making a sample API call."""
        self.ensure_one()
        # Placeholder for configuration test
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Configuration Test'),
                'message': _('Configuration for %s is valid.') % self.display_name,
                'type': 'success',
                'sticky': False,
            }
        }


class RingCentralAppConfigWizard(models.TransientModel):
    """Wizard to quickly set up app configurations."""
    
    _name = 'ringcentral.app.config.wizard'
    _description = 'Quick App Configuration Setup'
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    
    # Quick setup options
    crm_phone_id = fields.Many2one(
        'ringcentral.phone.number',
        string='CRM Phone Number',
        domain="[('can_be_caller_id', '=', True), ('company_id', '=', company_id)]",
    )
    
    sale_phone_id = fields.Many2one(
        'ringcentral.phone.number',
        string='Sales Phone Number',
        domain="[('can_be_caller_id', '=', True), ('company_id', '=', company_id)]",
    )
    
    hr_phone_id = fields.Many2one(
        'ringcentral.phone.number',
        string='HR Phone Number',
        domain="[('can_be_caller_id', '=', True), ('company_id', '=', company_id)]",
    )
    
    helpdesk_phone_id = fields.Many2one(
        'ringcentral.phone.number',
        string='Helpdesk Phone Number',
        domain="[('can_be_caller_id', '=', True), ('company_id', '=', company_id)]",
    )
    
    general_phone_id = fields.Many2one(
        'ringcentral.phone.number',
        string='General/Default Phone Number',
        domain="[('can_be_caller_id', '=', True), ('company_id', '=', company_id)]",
    )
    
    def action_apply_configuration(self):
        """Apply the quick configuration setup."""
        self.ensure_one()
        AppConfig = self.env['ringcentral.app.config']
        
        configs_to_create = []
        
        if self.crm_phone_id:
            configs_to_create.append({
                'app_type': 'crm',
                'phone_number_id': self.crm_phone_id.id,
                'company_id': self.company_id.id,
            })
        
        if self.sale_phone_id:
            configs_to_create.append({
                'app_type': 'sale',
                'phone_number_id': self.sale_phone_id.id,
                'company_id': self.company_id.id,
            })
        
        if self.hr_phone_id:
            configs_to_create.append({
                'app_type': 'hr',
                'phone_number_id': self.hr_phone_id.id,
                'company_id': self.company_id.id,
            })
        
        if self.helpdesk_phone_id:
            configs_to_create.append({
                'app_type': 'helpdesk',
                'phone_number_id': self.helpdesk_phone_id.id,
                'company_id': self.company_id.id,
            })
        
        if self.general_phone_id:
            configs_to_create.append({
                'app_type': 'general',
                'phone_number_id': self.general_phone_id.id,
                'company_id': self.company_id.id,
            })
        
        created_count = 0
        for config_vals in configs_to_create:
            existing = AppConfig.search([
                ('app_type', '=', config_vals['app_type']),
                ('company_id', '=', config_vals['company_id']),
            ], limit=1)
            
            if existing:
                existing.write({'phone_number_id': config_vals['phone_number_id']})
            else:
                AppConfig.create(config_vals)
                created_count += 1
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Configuration Applied'),
                'message': _('Successfully configured %d applications.') % len(configs_to_create),
                'type': 'success',
                'sticky': False,
            }
        }
