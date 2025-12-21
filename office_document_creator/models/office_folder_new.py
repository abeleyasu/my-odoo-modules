# -*- coding: utf-8 -*-
# Copyright 2025 Odoo Community
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""
Office Folder Model - Enterprise Document Management System

Google Drive-like folder organization with:
- Nested folder hierarchy
- Folder sharing with inheritance
- Folder colors
- Trash and restore
- Folder upload
"""

import secrets
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError

import logging
_logger = logging.getLogger(__name__)

# Folder colors (Google Drive style)
FOLDER_COLORS = [
    ('#9E9E9E', 'Default'),
    ('#F44336', 'Red'),
    ('#E91E63', 'Pink'),
    ('#9C27B0', 'Purple'),
    ('#673AB7', 'Deep Purple'),
    ('#3F51B5', 'Indigo'),
    ('#2196F3', 'Blue'),
    ('#03A9F4', 'Light Blue'),
    ('#00BCD4', 'Cyan'),
    ('#009688', 'Teal'),
    ('#4CAF50', 'Green'),
    ('#8BC34A', 'Light Green'),
    ('#CDDC39', 'Lime'),
    ('#FFEB3B', 'Yellow'),
    ('#FFC107', 'Amber'),
    ('#FF9800', 'Orange'),
    ('#FF5722', 'Deep Orange'),
    ('#795548', 'Brown'),
]


class OfficeFolder(models.Model):
    _name = 'office.folder'
    _description = 'Folder'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _parent_name = 'parent_id'
    _parent_store = True
    _order = 'name'

    # =========================================================================
    # BASIC FIELDS
    # =========================================================================
    
    name = fields.Char(
        string='Name',
        required=True,
        tracking=True,
        index=True,
    )
    description = fields.Text(
        string='Description',
    )
    
    # =========================================================================
    # HIERARCHY
    # =========================================================================
    
    parent_id = fields.Many2one(
        'office.folder',
        string='Parent Folder',
        ondelete='cascade',
        index=True,
    )
    parent_path = fields.Char(
        index=True,
        unaccent=False,
    )
    child_ids = fields.One2many(
        'office.folder',
        'parent_id',
        string='Subfolders',
    )
    
    # =========================================================================
    # CONTENT
    # =========================================================================
    
    document_ids = fields.One2many(
        'office.document',
        'folder_id',
        string='Documents',
        domain=[('is_trashed', '=', False)],
    )
    document_count = fields.Integer(
        string='Documents',
        compute='_compute_counts',
        store=True,
    )
    subfolder_count = fields.Integer(
        string='Subfolders',
        compute='_compute_counts',
        store=True,
    )
    total_size = fields.Integer(
        string='Total Size',
        compute='_compute_total_size',
    )
    total_size_human = fields.Char(
        string='Size',
        compute='_compute_total_size',
    )
    
    # =========================================================================
    # OWNERSHIP & ACCESS
    # =========================================================================
    
    owner_id = fields.Many2one(
        'res.users',
        string='Owner',
        default=lambda self: self.env.user,
        required=True,
        index=True,
    )
    
    # Folder-level access
    access_ids = fields.One2many(
        'office.document.access',
        'folder_id',
        string='Access Permissions',
    )
    access_count = fields.Integer(
        string='Shared With',
        compute='_compute_access_count',
    )
    
    # Legacy
    shared_user_ids = fields.Many2many(
        'res.users',
        'office_folder_share_rel',
        'folder_id',
        'user_id',
        string='Shared With (Legacy)',
    )
    
    # Share links
    share_link_ids = fields.One2many(
        'office.share.link',
        'folder_id',
        string='Share Links',
    )
    has_public_link = fields.Boolean(
        string='Has Public Link',
        compute='_compute_has_public_link',
    )
    
    # =========================================================================
    # DISPLAY
    # =========================================================================
    
    color = fields.Char(
        string='Color',
        default='#9E9E9E',
    )
    color_index = fields.Integer(
        string='Color Index',
        default=0,
    )
    icon = fields.Char(
        string='Icon',
        compute='_compute_icon',
    )
    
    is_starred = fields.Boolean(
        string='Starred',
        default=False,
        index=True,
    )
    
    # =========================================================================
    # TRASH
    # =========================================================================
    
    is_trashed = fields.Boolean(
        string='In Trash',
        default=False,
        index=True,
    )
    trashed_date = fields.Datetime(
        string='Trashed Date',
    )
    trashed_by = fields.Many2one(
        'res.users',
        string='Trashed By',
    )
    original_parent_id = fields.Many2one(
        'office.folder',
        string='Original Parent',
        help='Parent folder before moving to trash',
    )

    # =========================================================================
    # COMPUTED FIELDS
    # =========================================================================
    
    @api.depends('document_ids', 'child_ids')
    def _compute_counts(self):
        for folder in self:
            folder.document_count = len(folder.document_ids.filtered(
                lambda d: not d.is_trashed
            ))
            folder.subfolder_count = len(folder.child_ids.filtered(
                lambda f: not f.is_trashed
            ))

    def _compute_total_size(self):
        for folder in self:
            # Sum document sizes
            total = sum(folder.document_ids.mapped('file_size'))
            # Add subfolder sizes (recursive)
            for child in folder.child_ids:
                child._compute_total_size()
                total += child.total_size
            folder.total_size = total
            folder.total_size_human = self._format_size(total)

    def _format_size(self, size_bytes):
        if size_bytes < 1024:
            return f'{size_bytes} B'
        elif size_bytes < 1024 * 1024:
            return f'{size_bytes / 1024:.1f} KB'
        elif size_bytes < 1024 * 1024 * 1024:
            return f'{size_bytes / (1024 * 1024):.1f} MB'
        else:
            return f'{size_bytes / (1024 * 1024 * 1024):.2f} GB'

    @api.depends('access_ids')
    def _compute_access_count(self):
        for folder in self:
            folder.access_count = len(folder.access_ids)

    @api.depends('share_link_ids', 'share_link_ids.is_active')
    def _compute_has_public_link(self):
        for folder in self:
            folder.has_public_link = any(link.is_active for link in folder.share_link_ids)

    def _compute_icon(self):
        for folder in self:
            if folder.access_count > 0 or folder.has_public_link:
                folder.icon = 'fa-folder-open'  # Shared folder
            else:
                folder.icon = 'fa-folder'

    # =========================================================================
    # CONSTRAINTS
    # =========================================================================
    
    @api.constrains('parent_id')
    def _check_parent_recursion(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive folder hierarchy.'))

    @api.constrains('name', 'parent_id', 'owner_id')
    def _check_unique_name(self):
        for folder in self:
            domain = [
                ('id', '!=', folder.id),
                ('name', '=', folder.name),
                ('parent_id', '=', folder.parent_id.id if folder.parent_id else False),
                ('owner_id', '=', folder.owner_id.id),
                ('is_trashed', '=', False),
            ]
            if self.search_count(domain) > 0:
                raise ValidationError(_(
                    'A folder named "%s" already exists in this location.'
                ) % folder.name)

    # =========================================================================
    # CRUD
    # =========================================================================
    
    @api.model_create_multi
    def create(self, vals_list):
        folders = super().create(vals_list)
        for folder in folders:
            # Log activity
            self.env['office.document.activity'].log_activity(
                'folder', folder.id, 'create',
                description=f'Created folder "{folder.name}"'
            )
        return folders

    def unlink(self):
        for folder in self:
            # Log before delete
            self.env['office.document.activity'].log_activity(
                'folder', folder.id, 'delete',
                description=f'Permanently deleted folder "{folder.name}"'
            )
        return super().unlink()

    # =========================================================================
    # FOLDER OPERATIONS
    # =========================================================================
    
    @api.model
    def create_folder(self, name, parent_id=False):
        """Create a new folder.
        
        Args:
            name: Folder name
            parent_id: Optional parent folder ID
            
        Returns:
            Dict with folder info
        """
        name = (name or '').strip()
        if not name:
            raise ValidationError(_('Folder name cannot be empty.'))
        
        # Normalize parent_id
        parent_id = self._normalize_id(parent_id)
        
        folder = self.create({
            'name': name,
            'parent_id': parent_id or False,
            'owner_id': self.env.user.id,
        })
        
        _logger.info(f'Created folder: {name} (ID: {folder.id})')
        
        return {
            'id': folder.id,
            'name': folder.name,
            'parent_id': folder.parent_id.id if folder.parent_id else False,
            'color': folder.color,
        }

    def _normalize_id(self, value):
        """Normalize ID from various input formats."""
        if not value:
            return False
        if isinstance(value, dict):
            value = value.get('id', False)
        elif isinstance(value, (list, tuple)):
            value = value[0] if value else False
        try:
            return int(value) if value else False
        except (ValueError, TypeError):
            return False

    def action_open(self):
        """Open folder view."""
        self.ensure_one()
        return {
            'name': self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'office.document',
            'view_mode': 'kanban,list,form',
            'domain': [('folder_id', '=', self.id), ('is_trashed', '=', False)],
            'context': {'default_folder_id': self.id},
        }

    def action_rename(self, new_name):
        """Rename folder."""
        self.ensure_one()
        
        new_name = (new_name or '').strip()
        if not new_name:
            raise ValidationError(_('Name cannot be empty.'))
        
        old_name = self.name
        self.name = new_name
        
        # Log activity
        self.env['office.document.activity'].log_activity(
            'folder', self.id, 'rename',
            description=f'Renamed from "{old_name}" to "{new_name}"'
        )
        
        return True

    def action_set_color(self, color=None):
        """Set folder color or open color picker dialog."""
        self.ensure_one()
        if color:
            self.color = color
            return True
        # Return action to open color picker
        return {
            'name': _('Choose Color'),
            'type': 'ir.actions.act_window',
            'res_model': 'office.folder',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [[self.env.ref('office_document_creator.view_office_folder_color_wizard').id, 'form']],
            'target': 'new',
        }

    def action_save_color(self):
        """Save color and close dialog."""
        return {'type': 'ir.actions.act_window_close'}

    def action_toggle_star(self):
        """Toggle starred status."""
        self.ensure_one()
        self.is_starred = not self.is_starred
        return {'is_starred': self.is_starred}

    def action_move_to_trash(self):
        """Move folder to trash (with all contents)."""
        self.ensure_one()
        
        self.write({
            'is_trashed': True,
            'trashed_date': fields.Datetime.now(),
            'trashed_by': self.env.user.id,
            'original_parent_id': self.parent_id.id if self.parent_id else False,
            'parent_id': False,
        })
        
        # Also trash all documents
        for doc in self.document_ids:
            doc.action_move_to_trash()
        
        # Recursively trash subfolders
        for child in self.child_ids:
            child.action_move_to_trash()
        
        # Log activity
        self.env['office.document.activity'].log_activity(
            'folder', self.id, 'trash',
            description='Moved to trash'
        )
        
        return True

    def action_restore_from_trash(self):
        """Restore folder from trash."""
        self.ensure_one()
        
        self.write({
            'is_trashed': False,
            'trashed_date': False,
            'trashed_by': False,
            'parent_id': self.original_parent_id.id if self.original_parent_id else False,
            'original_parent_id': False,
        })
        
        # Restore documents
        trashed_docs = self.env['office.document'].search([
            ('original_folder_id', '=', self.id),
            ('is_trashed', '=', True),
        ])
        for doc in trashed_docs:
            doc.action_restore_from_trash()
        
        # Log activity
        self.env['office.document.activity'].log_activity(
            'folder', self.id, 'restore',
            description='Restored from trash'
        )
        
        return True

    def action_permanent_delete(self):
        """Permanently delete folder and all contents."""
        self.ensure_one()
        
        # Delete all documents
        self.document_ids.unlink()
        
        # Delete subfolders (recursive via cascade)
        self.unlink()
        
        return {'type': 'ir.actions.act_window_close'}

    def action_move(self, target_parent_id=False):
        """Move folder to new parent."""
        self.ensure_one()
        
        target_parent_id = self._normalize_id(target_parent_id)
        
        # Validate not moving to self or descendant
        if target_parent_id:
            target = self.browse(target_parent_id)
            if target.id == self.id:
                raise ValidationError(_('Cannot move folder into itself.'))
            if self.id in target._get_ancestor_ids():
                raise ValidationError(_('Cannot move folder into its descendant.'))
        
        old_parent = self.parent_id.name if self.parent_id else 'My Drive'
        self.parent_id = target_parent_id or False
        new_parent = self.parent_id.name if self.parent_id else 'My Drive'
        
        # Log activity
        self.env['office.document.activity'].log_activity(
            'folder', self.id, 'move',
            description=f'Moved from "{old_parent}" to "{new_parent}"'
        )
        
        return True

    def _get_ancestor_ids(self):
        """Get all ancestor folder IDs."""
        ancestors = []
        folder = self.parent_id
        while folder:
            ancestors.append(folder.id)
            folder = folder.parent_id
        return ancestors

    # =========================================================================
    # SHARING
    # =========================================================================
    
    def action_share(self):
        """Open share dialog."""
        self.ensure_one()
        return {
            'name': _('Share Folder "%s"') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'office.document.share.wizard',
            'view_mode': 'form',
            'views': [[False, 'form']],
            'target': 'new',
            'context': {'default_folder_id': self.id},
        }

    def get_access_list(self):
        """Get list of users with access."""
        self.ensure_one()
        return self.env['office.document.access'].get_access_list('folder', self.id)

    def grant_access(self, user_id, permission='viewer', notify=True):
        """Grant access (with inheritance to contents)."""
        self.ensure_one()
        return self.env['office.document.access'].grant_access(
            'folder', self.id, user_id, permission, notify
        )

    def revoke_access(self, user_id):
        """Revoke access."""
        self.ensure_one()
        return self.env['office.document.access'].revoke_access(
            'folder', self.id, user_id
        )

    # =========================================================================
    # QUERY METHODS
    # =========================================================================
    
    @api.model
    def get_folder_tree(self, parent_id=False):
        """Get folder tree structure for navigation.
        
        Optimized to fetch all folders in single query.
        """
        # Fetch all user's folders in one query
        all_folders = self.search([
            ('owner_id', '=', self.env.user.id),
            ('is_trashed', '=', False),
        ], order='name')
        
        # Build tree structure
        def build_tree(parent_id):
            children = all_folders.filtered(
                lambda f: (f.parent_id.id if f.parent_id else False) == parent_id
            )
            return [{
                'id': f.id,
                'name': f.name,
                'color': f.color,
                'icon': f.icon,
                'document_count': f.document_count,
                'subfolder_count': f.subfolder_count,
                'is_starred': f.is_starred,
                'has_public_link': f.has_public_link,
                'access_count': f.access_count,
                'children': build_tree(f.id),
            } for f in children]
        
        return build_tree(parent_id if parent_id else False)

    @api.model
    def get_folder_path(self, folder_id):
        """Get breadcrumb path from root to folder."""
        folder_id = self._normalize_id(folder_id) if hasattr(self, '_normalize_id') else folder_id
        
        if not folder_id:
            return []
        
        path = []
        folder = self.browse(folder_id)
        
        while folder.exists():
            path.insert(0, {
                'id': folder.id,
                'name': folder.name,
            })
            folder = folder.parent_id
        
        return path

    @api.model
    def get_subfolders(self, parent_id=False):
        """Get immediate subfolders of a folder."""
        parent_id = self._normalize_id(parent_id) if hasattr(self, '_normalize_id') else parent_id
        
        folders = self.search([
            ('owner_id', '=', self.env.user.id),
            ('parent_id', '=', parent_id if parent_id else False),
            ('is_trashed', '=', False),
        ], order='name')
        
        return [{
            'id': f.id,
            'name': f.name,
            'color': f.color,
            'icon': f.icon,
            'document_count': f.document_count,
            'subfolder_count': f.subfolder_count,
            'is_starred': f.is_starred,
        } for f in folders]

    @api.model
    def get_trash_folders(self):
        """Get folders in trash."""
        folders = self.search([
            ('owner_id', '=', self.env.user.id),
            ('is_trashed', '=', True),
        ], order='trashed_date desc')
        
        return [{
            'id': f.id,
            'name': f.name,
            'color': f.color,
            'trashed_date': f.trashed_date.isoformat() if f.trashed_date else None,
        } for f in folders]

    @api.model
    def empty_trash(self):
        """Permanently delete all trashed folders."""
        trashed = self.search([
            ('owner_id', '=', self.env.user.id),
            ('is_trashed', '=', True),
        ])
        count = len(trashed)
        trashed.unlink()
        return count

    @api.model
    def get_folder_colors(self):
        """Get available folder colors."""
        return FOLDER_COLORS
