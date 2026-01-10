# -*- coding: utf-8 -*-
"""
RingCentral Extension Model
===========================

Represents RingCentral extensions synced from the RingCentral account.
Extensions can be users, call queues, IVR menus, etc.

Industry Standard Implementation:
- Synced from RingCentral API /restapi/v1.0/account/~/extension
- Supports all extension types (User, Department/Queue, Announcement, etc.)
- Links to Odoo users for user-type extensions
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class RingCentralExtension(models.Model):
    """RingCentral Extension synchronized from RC account."""
    
    _name = 'ringcentral.extension'
    _description = 'RingCentral Extension'
    _order = 'extension_number, name'
    _rec_name = 'display_name'
    
    # ===========================
    # Core Fields
    # ===========================
    
    name = fields.Char(
        string='Name',
        required=True,
        help='Extension name from RingCentral'
    )
    
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
    )
    
    rc_extension_id = fields.Char(
        string='RC Extension ID',
        required=True,
        index=True,
        help='RingCentral internal extension ID'
    )
    
    extension_number = fields.Char(
        string='Extension Number',
        index=True,
        help='Internal dial extension number (e.g., 101, 102)'
    )
    
    extension_type = fields.Selection([
        ('User', 'User'),
        ('Department', 'Call Queue'),
        ('Announcement', 'Announcement'),
        ('Voicemail', 'Voicemail Only'),
        ('SharedLinesGroup', 'Shared Lines Group'),
        ('PagingOnly', 'Paging Only'),
        ('IvrMenu', 'IVR Menu'),
        ('ApplicationExtension', 'Application'),
        ('ParkLocation', 'Park Location'),
        ('Limited', 'Limited'),
        ('Bot', 'Bot'),
        ('ProxyAdmin', 'Proxy Admin'),
        ('DelegatedLinesGroup', 'Delegated Lines'),
        ('GroupCallPickup', 'Group Call Pickup'),
        ('Room', 'Room'),
        ('FlexibleUser', 'Flexible User'),
        ('VirtualUser', 'Virtual User'),
        ('Site', 'Site'),
    ], string='Extension Type',
       default='User',
       help='Type of extension in RingCentral')
    
    status = fields.Selection([
        ('Enabled', 'Enabled'),
        ('Disabled', 'Disabled'),
        ('Frozen', 'Frozen'),
        ('NotActivated', 'Not Activated'),
        ('Unassigned', 'Unassigned'),
    ], string='Status',
       default='Enabled',
       help='Extension status in RingCentral')
    
    # ===========================
    # Contact Information
    # ===========================
    
    email = fields.Char(
        string='Email',
        help='Email associated with this extension'
    )
    
    contact_phone = fields.Char(
        string='Contact Phone',
        help='Contact phone for this extension'
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
    
    user_id = fields.Many2one(
        'res.users',
        string='Linked Odoo User',
        help='Odoo user linked to this RingCentral extension',
        ondelete='set null',
    )
    
    phone_number_ids = fields.One2many(
        'ringcentral.phone.number',
        'extension_id',
        string='Phone Numbers',
        help='Phone numbers assigned to this extension'
    )
    
    phone_number_count = fields.Integer(
        string='Phone Number Count',
        compute='_compute_phone_number_count',
    )
    
    call_queue_id = fields.Many2one(
        'ringcentral.call.queue',
        string='Call Queue',
        compute='_compute_call_queue',
        help='If this extension is a call queue'
    )
    
    # ===========================
    # Computed Fields
    # ===========================
    
    primary_phone = fields.Char(
        string='Primary Phone',
        compute='_compute_primary_phone',
        help='Primary phone number for this extension'
    )
    
    is_user_extension = fields.Boolean(
        string='Is User Extension',
        compute='_compute_is_user_extension',
        store=True,
    )
    
    is_queue_extension = fields.Boolean(
        string='Is Queue Extension',
        compute='_compute_is_queue_extension',
        store=True,
    )
    
    # ===========================
    # Sync Tracking
    # ===========================
    
    last_sync_date = fields.Datetime(
        string='Last Synced',
        help='Last time this extension was synced from RingCentral'
    )
    
    rc_data_json = fields.Text(
        string='RC Data (JSON)',
        help='Raw JSON data from RingCentral API (for debugging)'
    )
    
    # ===========================
    # Computed Methods
    # ===========================
    
    @api.depends('name', 'extension_number', 'extension_type')
    def _compute_display_name(self):
        for ext in self:
            parts = []
            if ext.extension_number:
                parts.append(f"[{ext.extension_number}]")
            parts.append(ext.name or 'Unnamed')
            if ext.extension_type and ext.extension_type != 'User':
                parts.append(f"({ext.extension_type})")
            ext.display_name = ' '.join(parts)
    
    @api.depends('phone_number_ids')
    def _compute_phone_number_count(self):
        for ext in self:
            ext.phone_number_count = len(ext.phone_number_ids)
    
    @api.depends('phone_number_ids', 'phone_number_ids.is_primary')
    def _compute_primary_phone(self):
        for ext in self:
            primary = ext.phone_number_ids.filtered(lambda p: p.is_primary)[:1]
            if not primary:
                primary = ext.phone_number_ids[:1]
            ext.primary_phone = primary.phone_number if primary else False
    
    @api.depends('extension_type')
    def _compute_is_user_extension(self):
        for ext in self:
            ext.is_user_extension = ext.extension_type in ('User', 'VirtualUser', 'FlexibleUser')
    
    @api.depends('extension_type')
    def _compute_is_queue_extension(self):
        for ext in self:
            ext.is_queue_extension = ext.extension_type == 'Department'
    
    def _compute_call_queue(self):
        CallQueue = self.env['ringcentral.call.queue']
        for ext in self:
            if ext.is_queue_extension:
                ext.call_queue_id = CallQueue.search([
                    ('rc_extension_id', '=', ext.rc_extension_id),
                    ('company_id', '=', ext.company_id.id),
                ], limit=1)
            else:
                ext.call_queue_id = False
    
    # ===========================
    # Constraints
    # ===========================
    
    _sql_constraints = [
        ('rc_extension_company_unique',
         'UNIQUE(rc_extension_id, company_id)',
         'RingCentral extension ID must be unique per company.'),
    ]
    
    # ===========================
    # Actions
    # ===========================
    
    def action_sync_from_ringcentral(self):
        """Manually sync this extension from RingCentral."""
        self.ensure_one()
        sync = self.env['ringcentral.sync']
        sync._sync_single_extension(self.rc_extension_id, self.company_id)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Extension Synced'),
                'message': _('Extension %s has been synced from RingCentral.') % self.name,
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_link_to_user(self):
        """Open wizard to link this extension to an Odoo user."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Link to User'),
            'res_model': 'ringcentral.extension',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_view_phone_numbers(self):
        """View phone numbers for this extension."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Phone Numbers'),
            'res_model': 'ringcentral.phone.number',
            'view_mode': 'tree,form',
            'domain': [('extension_id', '=', self.id)],
            'context': {'default_extension_id': self.id},
        }
