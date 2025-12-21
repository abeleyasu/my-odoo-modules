# -*- coding: utf-8 -*-
# Copyright 2025 Odoo Community
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

import secrets
from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError

import logging
_logger = logging.getLogger(__name__)


class OfficeDocumentAccess(models.Model):
    """Track individual access permissions for documents and folders.
    
    This model provides Google Drive-like sharing with:
    - Individual user access with permission levels
    - Inherited permissions from parent folders
    - Access visibility (who has access)
    - Activity tracking
    """
    _name = 'office.document.access'
    _description = 'Document Access Permission'
    _order = 'create_date desc'
    _rec_name = 'user_id'

    # Access target (document or folder - polymorphic)
    document_id = fields.Many2one(
        'office.document',
        string='Document',
        ondelete='cascade',
        index=True,
    )
    folder_id = fields.Many2one(
        'office.folder',
        string='Folder',
        ondelete='cascade',
        index=True,
    )
    
    # Who has access
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        ondelete='cascade',
        index=True,
    )
    
    # Permission level (Google Drive style)
    permission = fields.Selection([
        ('viewer', 'Viewer'),
        ('commenter', 'Commenter'),
        ('editor', 'Editor'),
    ], string='Permission', default='viewer', required=True)
    
    # Who granted access
    granted_by = fields.Many2one(
        'res.users',
        string='Granted By',
        default=lambda self: self.env.user,
        required=True,
    )
    granted_date = fields.Datetime(
        string='Granted Date',
        default=fields.Datetime.now,
    )
    
    # Inheritance tracking
    is_inherited = fields.Boolean(
        string='Inherited',
        default=False,
        help='True if permission is inherited from parent folder',
    )
    inherited_from_folder_id = fields.Many2one(
        'office.folder',
        string='Inherited From',
        ondelete='cascade',
    )
    
    # Notification preferences
    notify_on_share = fields.Boolean(
        string='Notify on Share',
        default=True,
    )
    notify_on_change = fields.Boolean(
        string='Notify on Changes',
        default=False,
    )
    
    # Access tracking
    last_accessed = fields.Datetime(
        string='Last Accessed',
    )
    access_count = fields.Integer(
        string='Access Count',
        default=0,
    )

    _sql_constraints = [
        ('unique_document_user', 
         'UNIQUE(document_id, user_id)', 
         'User already has access to this document.'),
        ('unique_folder_user', 
         'UNIQUE(folder_id, user_id)', 
         'User already has access to this folder.'),
        ('check_target',
         'CHECK((document_id IS NOT NULL AND folder_id IS NULL) OR (document_id IS NULL AND folder_id IS NOT NULL))',
         'Access must be for either a document or a folder, not both.'),
    ]

    @api.model
    def grant_access(self, target_type, target_id, user_id, permission='viewer', notify=True):
        """Grant access to a document or folder.
        
        Args:
            target_type: 'document' or 'folder'
            target_id: ID of the document or folder
            user_id: ID of the user to grant access
            permission: 'viewer', 'commenter', or 'editor'
            notify: Whether to send email notification
            
        Returns:
            The created access record
        """
        vals = {
            'user_id': user_id,
            'permission': permission,
            'granted_by': self.env.user.id,
            'notify_on_share': notify,
        }
        
        if target_type == 'document':
            vals['document_id'] = target_id
            # Check if user is owner
            doc = self.env['office.document'].browse(target_id)
            if doc.owner_id.id == user_id:
                raise ValidationError(_('Cannot share with the owner.'))
        else:
            vals['folder_id'] = target_id
            folder = self.env['office.folder'].browse(target_id)
            if folder.owner_id.id == user_id:
                raise ValidationError(_('Cannot share with the owner.'))
        
        # Check for existing access
        domain = [('user_id', '=', user_id)]
        if target_type == 'document':
            domain.append(('document_id', '=', target_id))
        else:
            domain.append(('folder_id', '=', target_id))
        
        existing = self.search(domain, limit=1)
        if existing:
            # Update permission
            existing.write({'permission': permission})
            return existing
        
        access = self.create(vals)
        
        # Send notification
        if notify:
            self._send_share_notification(access)
        
        # If folder, propagate to children
        if target_type == 'folder':
            self._propagate_folder_access(target_id, user_id, permission)
        
        return access

    def _propagate_folder_access(self, folder_id, user_id, permission):
        """Propagate folder access to all children (documents and subfolders)."""
        folder = self.env['office.folder'].browse(folder_id)
        
        # Propagate to documents
        for doc in folder.document_ids:
            existing = self.search([
                ('document_id', '=', doc.id),
                ('user_id', '=', user_id),
            ], limit=1)
            
            if not existing:
                self.create({
                    'document_id': doc.id,
                    'user_id': user_id,
                    'permission': permission,
                    'granted_by': self.env.user.id,
                    'is_inherited': True,
                    'inherited_from_folder_id': folder_id,
                })
        
        # Propagate to subfolders
        for subfolder in folder.child_ids:
            existing = self.search([
                ('folder_id', '=', subfolder.id),
                ('user_id', '=', user_id),
            ], limit=1)
            
            if not existing:
                self.create({
                    'folder_id': subfolder.id,
                    'user_id': user_id,
                    'permission': permission,
                    'granted_by': self.env.user.id,
                    'is_inherited': True,
                    'inherited_from_folder_id': folder_id,
                })
            
            # Recurse
            self._propagate_folder_access(subfolder.id, user_id, permission)

    def _send_share_notification(self, access):
        """Send email notification when document is shared."""
        # TODO: Implement email notification
        _logger.info(f'Share notification: {access.user_id.name} granted {access.permission} access')

    @api.model
    def revoke_access(self, target_type, target_id, user_id):
        """Revoke access from a user."""
        domain = [('user_id', '=', user_id)]
        if target_type == 'document':
            domain.append(('document_id', '=', target_id))
        else:
            domain.append(('folder_id', '=', target_id))
        
        access = self.search(domain)
        if access:
            access.unlink()
        
        # If folder, also revoke inherited access
        if target_type == 'folder':
            inherited = self.search([
                ('inherited_from_folder_id', '=', target_id),
                ('user_id', '=', user_id),
            ])
            inherited.unlink()
        
        return True

    @api.model
    def get_access_list(self, target_type, target_id):
        """Get list of all users with access to a document or folder.
        
        Returns list of dicts with user info and permission level.
        """
        domain = []
        if target_type == 'document':
            domain.append(('document_id', '=', target_id))
            doc = self.env['office.document'].browse(target_id)
            owner = doc.owner_id
        else:
            domain.append(('folder_id', '=', target_id))
            folder = self.env['office.folder'].browse(target_id)
            owner = folder.owner_id
        
        access_list = []
        
        # Add owner first
        access_list.append({
            'user_id': owner.id,
            'user_name': owner.name,
            'user_email': owner.email or owner.login,
            'user_avatar': f'/web/image/res.users/{owner.id}/avatar_128',
            'permission': 'owner',
            'is_owner': True,
            'is_inherited': False,
            'granted_by': None,
            'granted_date': None,
        })
        
        # Add shared users
        for rec in self.search(domain):
            access_list.append({
                'user_id': rec.user_id.id,
                'user_name': rec.user_id.name,
                'user_email': rec.user_id.email or rec.user_id.login,
                'user_avatar': f'/web/image/res.users/{rec.user_id.id}/avatar_128',
                'permission': rec.permission,
                'is_owner': False,
                'is_inherited': rec.is_inherited,
                'inherited_from': rec.inherited_from_folder_id.name if rec.inherited_from_folder_id else None,
                'granted_by': rec.granted_by.name,
                'granted_date': rec.granted_date.isoformat() if rec.granted_date else None,
            })
        
        return access_list

    def track_access(self):
        """Track when user accesses the document."""
        self.write({
            'last_accessed': fields.Datetime.now(),
            'access_count': self.access_count + 1,
        })


class OfficeShareLink(models.Model):
    """Public share links for documents and folders (Google Drive style)."""
    _name = 'office.share.link'
    _description = 'Public Share Link'
    _order = 'create_date desc'

    # Link target
    document_id = fields.Many2one(
        'office.document',
        string='Document',
        ondelete='cascade',
        index=True,
    )
    folder_id = fields.Many2one(
        'office.folder',
        string='Folder',
        ondelete='cascade',
        index=True,
    )
    
    # Link token (unique identifier)
    token = fields.Char(
        string='Token',
        required=True,
        index=True,
        default=lambda self: secrets.token_urlsafe(32),
    )
    
    # Link settings
    is_active = fields.Boolean(
        string='Active',
        default=True,
    )
    permission = fields.Selection([
        ('viewer', 'Anyone with link can view'),
        ('commenter', 'Anyone with link can comment'),
        ('editor', 'Anyone with link can edit'),
    ], string='Permission', default='viewer', required=True)
    
    # Security settings
    requires_password = fields.Boolean(
        string='Password Protected',
        default=False,
    )
    password_hash = fields.Char(
        string='Password Hash',
    )
    
    # Expiration
    has_expiry = fields.Boolean(
        string='Has Expiry',
        default=False,
    )
    expiry_date = fields.Datetime(
        string='Expiry Date',
    )
    
    # Restrictions
    allow_download = fields.Boolean(
        string='Allow Download',
        default=True,
    )
    allow_copy = fields.Boolean(
        string='Allow Copy',
        default=True,
    )
    
    # Usage tracking
    view_count = fields.Integer(
        string='View Count',
        default=0,
    )
    last_viewed = fields.Datetime(
        string='Last Viewed',
    )
    
    # Created by
    created_by = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user,
    )

    _sql_constraints = [
        ('unique_token', 'UNIQUE(token)', 'Token must be unique.'),
    ]

    def get_share_url(self):
        """Get the full share URL."""
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base_url}/office/share/{self.token}"

    def validate_access(self, password=None):
        """Validate if the link is accessible.
        
        Returns: (is_valid, error_message)
        """
        self.ensure_one()
        
        if not self.is_active:
            return False, _('This link has been disabled.')
        
        if self.has_expiry and self.expiry_date:
            if fields.Datetime.now() > self.expiry_date:
                return False, _('This link has expired.')
        
        if self.requires_password:
            if not password:
                return False, _('Password required.')
            # Simple hash check (in production, use proper hashing)
            import hashlib
            if hashlib.sha256(password.encode()).hexdigest() != self.password_hash:
                return False, _('Incorrect password.')
        
        return True, None

    def track_view(self):
        """Track link usage."""
        self.write({
            'view_count': self.view_count + 1,
            'last_viewed': fields.Datetime.now(),
        })

    @api.model
    def create_link(self, target_type, target_id, permission='viewer', 
                    password=None, expiry_days=None, allow_download=True):
        """Create a new share link.
        
        Args:
            target_type: 'document' or 'folder'
            target_id: ID of document or folder
            permission: 'viewer', 'commenter', 'editor'
            password: Optional password protection
            expiry_days: Optional expiry in days
            allow_download: Whether to allow download
            
        Returns: Share link record
        """
        vals = {
            'permission': permission,
            'allow_download': allow_download,
            'created_by': self.env.user.id,
        }
        
        if target_type == 'document':
            vals['document_id'] = target_id
        else:
            vals['folder_id'] = target_id
        
        if password:
            import hashlib
            vals['requires_password'] = True
            vals['password_hash'] = hashlib.sha256(password.encode()).hexdigest()
        
        if expiry_days:
            vals['has_expiry'] = True
            vals['expiry_date'] = fields.Datetime.now() + timedelta(days=expiry_days)
        
        return self.create(vals)

    @api.model
    def get_link_for_target(self, target_type, target_id):
        """Get existing share link for a document or folder."""
        domain = [('is_active', '=', True)]
        if target_type == 'document':
            domain.append(('document_id', '=', target_id))
        else:
            domain.append(('folder_id', '=', target_id))
        
        return self.search(domain, limit=1)

    @api.model
    def create_share_link(self, target_type, target_id, permission='viewer',
                          password=None, expiry_days=None, allow_download=True):
        """Alias for create_link for backward compatibility with tests."""
        return self.create_link(target_type, target_id, permission, 
                                password, expiry_days, allow_download)
