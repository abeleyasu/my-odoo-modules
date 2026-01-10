# -*- coding: utf-8 -*-
"""
Extend res.users with RingCentral multi-line configuration.

Adds:
- Link to user's RingCentral extension
- Personal default phone number for outbound calls
- Override settings for per-app configuration
"""

from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    """Extend users with RingCentral multi-line settings."""
    
    _inherit = 'res.users'
    
    # ===========================
    # RingCentral Extension Link
    # ===========================
    
    # Note: Use rc_multiline_ext_id to avoid conflict with ringcentral_base
    # which already defines ringcentral_extension_id as a Char field
    rc_multiline_ext_id = fields.Many2one(
        'ringcentral.extension',
        string='RingCentral Extension (Synced)',
        ondelete='set null',
        domain="[('extension_type', 'in', ['User', 'VirtualUser']), ('company_id', '=', company_id)]",
        help='The RingCentral extension record synced from API'
    )
    
    rc_multiline_ext_number = fields.Char(
        related='rc_multiline_ext_id.extension_number',
        string='Extension Number (Synced)',
        readonly=True,
    )
    
    rc_multiline_ext_status = fields.Selection(
        related='rc_multiline_ext_id.status',
        string='Extension Status',
        readonly=True,
    )
    
    # ===========================
    # Default Phone Number
    # ===========================
    
    ringcentral_default_from_number_id = fields.Many2one(
        'ringcentral.phone.number',
        string='Default Caller ID',
        ondelete='set null',
        domain="[('can_be_caller_id', '=', True), ('company_id', '=', company_id)]",
        help='Default phone number for outbound calls (overrides app config)'
    )
    
    ringcentral_default_from_number = fields.Char(
        related='ringcentral_default_from_number_id.phone_number',
        string='Default Phone',
        readonly=True,
    )
    
    # ===========================
    # Override Settings
    # ===========================
    
    ringcentral_use_personal_number = fields.Boolean(
        string='Use Personal Number',
        default=False,
        help='Always use personal default number instead of app-specific numbers'
    )
    
    ringcentral_can_change_caller_id = fields.Boolean(
        string='Can Change Caller ID',
        default=True,
        help='Allow this user to select different caller IDs in the widget'
    )
    
    # ===========================
    # Available Phone Numbers
    # ===========================
    
    ringcentral_available_number_ids = fields.Many2many(
        'ringcentral.phone.number',
        'res_users_ringcentral_phone_number_rel',
        'user_id',
        'phone_number_id',
        string='Available Phone Numbers',
        domain="[('can_be_caller_id', '=', True), ('company_id', '=', company_id)]",
        help='Phone numbers this user can use as caller ID'
    )
    
    ringcentral_available_number_count = fields.Integer(
        string='Available Numbers',
        compute='_compute_available_numbers',
    )
    
    # ===========================
    # Computed Methods
    # ===========================
    
    @api.depends('ringcentral_available_number_ids')
    def _compute_available_numbers(self):
        for user in self:
            user.ringcentral_available_number_count = len(user.ringcentral_available_number_ids)
    
    # ===========================
    # Business Methods
    # ===========================
    
    def get_ringcentral_caller_id(self, app_type='general'):
        """
        Get the appropriate caller ID for this user in a given app context.
        
        Priority:
        1. If use_personal_number is True, use default_from_number
        2. Otherwise, use app configuration
        
        :param app_type: Application type (crm, sale, hr, etc.)
        :return: phone_number string or False
        """
        self.ensure_one()
        
        # Check if user wants to always use personal number
        if self.ringcentral_use_personal_number and self.ringcentral_default_from_number_id:
            return self.ringcentral_default_from_number_id.phone_number
        
        # Get from app config
        AppConfig = self.env['ringcentral.app.config']
        result = AppConfig.get_phone_number_for_context({
            'app_type': app_type,
            'user_id': self.id,
            'company_id': self.company_id.id,
        })
        
        return result.get('phone_number') or False
    
    def get_available_caller_ids(self):
        """
        Get all available caller IDs for this user.
        
        Returns:
            List of dicts with phone_number, formatted_number, label
        """
        self.ensure_one()
        
        result = []
        
        # Add user's specific available numbers
        for phone in self.ringcentral_available_number_ids:
            result.append({
                'id': phone.id,
                'phone_number': phone.phone_number,
                'formatted_number': phone.formatted_number or phone.phone_number,
                'label': phone.display_name,
                'source': 'user_assigned',
            })
        
        # Add extension's phone numbers if not already included
        if self.rc_multiline_ext_id:
            for phone in self.rc_multiline_ext_id.phone_number_ids:
                if phone.id not in [p['id'] for p in result] and phone.can_be_caller_id:
                    result.append({
                        'id': phone.id,
                        'phone_number': phone.phone_number,
                        'formatted_number': phone.formatted_number or phone.phone_number,
                        'label': f"{phone.display_name} (Extension)",
                        'source': 'extension',
                    })
        
        # Add company phone numbers (for admins or if no others available)
        if not result or self.has_group('ringcentral_multiline.group_ringcentral_manager'):
            company_phones = self.env['ringcentral.phone.number'].search([
                ('company_id', '=', self.company_id.id),
                ('can_be_caller_id', '=', True),
            ], limit=10)
            
            for phone in company_phones:
                if phone.id not in [p['id'] for p in result]:
                    result.append({
                        'id': phone.id,
                        'phone_number': phone.phone_number,
                        'formatted_number': phone.formatted_number or phone.phone_number,
                        'label': f"{phone.display_name} (Company)",
                        'source': 'company',
                    })
        
        return result
    
    def action_link_ringcentral_extension(self):
        """
        Open wizard to link this user to a RingCentral extension.
        
        Can auto-match by email if extension exists.
        """
        self.ensure_one()
        
        # Try auto-match by email
        Extension = self.env['ringcentral.extension']
        matching = Extension.search([
            ('email', '=', self.email),
            ('company_id', '=', self.company_id.id),
            ('extension_type', 'in', ['User', 'VirtualUser']),
        ], limit=1)
        
        if matching:
            self.rc_multiline_ext_id = matching
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Extension Linked'),
                    'message': _('Automatically linked to extension %s') % matching.name,
                    'type': 'success',
                    'sticky': False,
                }
            }
        
        # Open selection view
        return {
            'type': 'ir.actions.act_window',
            'name': _('Select Extension'),
            'res_model': 'ringcentral.extension',
            'view_mode': 'tree,form',
            'domain': [
                ('company_id', '=', self.company_id.id),
                ('extension_type', 'in', ['User', 'VirtualUser']),
                ('user_id', '=', False),  # Not already linked
            ],
            'context': {
                'link_to_user_id': self.id,
            },
            'target': 'new',
        }
    
    def action_sync_extension(self):
        """Sync this user's extension data from RingCentral."""
        self.ensure_one()
        
        if not self.rc_multiline_ext_id:
            raise models.UserError(_('No RingCentral extension linked to this user.'))
        
        return self.rc_multiline_ext_id.action_sync_from_ringcentral()
    
    def action_view_available_numbers(self):
        """View all phone numbers available to this user."""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Available Phone Numbers'),
            'res_model': 'ringcentral.phone.number',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.ringcentral_available_number_ids.ids)],
        }
    
    # ===========================
    # Auto-linking Methods
    # ===========================
    
    @api.model
    def auto_link_extensions_by_email(self, company=None):
        """
        Auto-link users to extensions based on matching email addresses.
        
        :param company: res.company record (defaults to current company)
        :return: Dict with results
        """
        company = company or self.env.company
        
        results = {
            'linked': 0,
            'already_linked': 0,
            'no_match': 0,
        }
        
        users = self.search([
            ('company_id', '=', company.id),
            ('rc_multiline_ext_id', '=', False),
            ('email', '!=', False),
        ])
        
        Extension = self.env['ringcentral.extension']
        
        for user in users:
            if user.rc_multiline_ext_id:
                results['already_linked'] += 1
                continue
            
            matching = Extension.search([
                ('email', '=ilike', user.email),
                ('company_id', '=', company.id),
                ('extension_type', 'in', ['User', 'VirtualUser']),
                ('user_id', '=', False),
            ], limit=1)
            
            if matching:
                user.rc_multiline_ext_id = matching
                matching.user_id = user
                results['linked'] += 1
                _logger.info(f"Auto-linked user {user.name} to extension {matching.name}")
            else:
                results['no_match'] += 1
        
        return results


class ResUsersRingCentralPreferences(models.Model):
    """Inherit to add RingCentral fields to user preferences form."""
    
    _inherit = 'res.users'
    
    # Make these fields visible in preferences
    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + [
            'rc_multiline_ext_id',
            'rc_multiline_ext_number',
            'ringcentral_default_from_number_id',
            'ringcentral_default_from_number',
            'ringcentral_use_personal_number',
            'ringcentral_can_change_caller_id',
            'ringcentral_available_number_ids',
        ]
    
    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + [
            'ringcentral_default_from_number_id',
            'ringcentral_use_personal_number',
        ]
