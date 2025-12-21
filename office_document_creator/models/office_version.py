# -*- coding: utf-8 -*-
# Copyright 2025 Odoo Community
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

import base64
from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)


class OfficeDocumentVersion(models.Model):
    """Version history for documents (Google Drive style).
    
    Features:
    - Automatic versioning on save
    - Named versions
    - Version restore
    - Version comparison
    - Version cleanup (configurable retention)
    """
    _name = 'office.document.version'
    _description = 'Document Version'
    _order = 'version_number desc'

    document_id = fields.Many2one(
        'office.document',
        string='Document',
        required=True,
        ondelete='cascade',
        index=True,
    )
    
    # Version identification
    version_number = fields.Integer(
        string='Version',
        required=True,
    )
    version_name = fields.Char(
        string='Version Name',
        help='Optional name for this version (e.g., "Final Draft")',
    )
    
    # Version content
    attachment_id = fields.Many2one(
        'ir.attachment',
        string='File',
        required=True,
        ondelete='cascade',
    )
    file_size = fields.Integer(
        string='File Size',
        related='attachment_id.file_size',
        store=True,
    )
    checksum = fields.Char(
        string='Checksum',
        related='attachment_id.checksum',
        store=True,
    )
    
    # Metadata
    created_by = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user,
        required=True,
    )
    create_date = fields.Datetime(
        string='Created',
        default=fields.Datetime.now,
    )
    
    # Change description
    change_summary = fields.Text(
        string='Changes',
        help='Summary of changes in this version',
    )
    
    # Keep permanently flag
    is_pinned = fields.Boolean(
        string='Keep Forever',
        default=False,
        help='If checked, this version will not be auto-deleted',
    )

    @api.model
    def create_version(self, document_id, attachment_data=None, name=None, summary=None):
        """Create a new version of a document.
        
        Args:
            document_id: ID of the document
            attachment_data: Base64 encoded file data (optional, uses current if not provided)
            name: Optional version name
            summary: Optional change summary
            
        Returns: The created version record
        """
        document = self.env['office.document'].browse(document_id)
        if not document.exists():
            raise UserError(_('Document not found.'))
        
        # Get next version number
        last_version = self.search([
            ('document_id', '=', document_id)
        ], limit=1, order='version_number desc')
        
        next_number = (last_version.version_number + 1) if last_version else 1
        
        # Create attachment copy
        if attachment_data:
            attachment = self.env['ir.attachment'].create({
                'name': f"{document.name}_v{next_number}",
                'datas': attachment_data,
                'mimetype': document.attachment_id.mimetype,
                'res_model': 'office.document.version',
            })
        else:
            # Copy current attachment
            attachment = document.attachment_id.copy({
                'name': f"{document.name}_v{next_number}",
                'res_model': 'office.document.version',
            })
        
        version = self.create({
            'document_id': document_id,
            'version_number': next_number,
            'version_name': name,
            'attachment_id': attachment.id,
            'change_summary': summary,
        })
        
        # Link attachment
        attachment.res_id = version.id
        
        # Cleanup old versions
        self._cleanup_old_versions(document_id)
        
        _logger.info(f'Created version {next_number} for document {document.name}')
        return version

    def _cleanup_old_versions(self, document_id, keep_count=100, keep_days=30):
        """Remove old versions based on retention policy.
        
        Keeps:
        - Last `keep_count` versions
        - Versions from last `keep_days` days
        - Pinned versions
        """
        from datetime import timedelta
        
        cutoff_date = fields.Datetime.now() - timedelta(days=keep_days)
        
        # Get all versions except pinned
        all_versions = self.search([
            ('document_id', '=', document_id),
            ('is_pinned', '=', False),
        ], order='version_number desc')
        
        # Keep recent by count
        to_delete = all_versions[keep_count:]
        
        # Filter: only delete if also older than cutoff
        to_delete = to_delete.filtered(
            lambda v: v.create_date < cutoff_date
        )
        
        if to_delete:
            _logger.info(f'Cleaning up {len(to_delete)} old versions')
            to_delete.unlink()

    def restore(self):
        """Restore this version as the current document version."""
        self.ensure_one()
        document = self.document_id
        
        # Create new version from current before restore
        self.create_version(
            document.id,
            name=f"Before restore to v{self.version_number}",
            summary=f"Auto-saved before restoring to version {self.version_number}"
        )
        
        # Copy version content to current document
        document.attachment_id.write({
            'datas': self.attachment_id.datas,
        })
        
        _logger.info(f'Restored document {document.name} to version {self.version_number}')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Version Restored'),
                'message': _('Document restored to version %s') % self.version_number,
                'type': 'success',
            }
        }

    def download(self):
        """Download this version."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.attachment_id.id}?download=true',
            'target': 'self',
        }

    @api.model
    def get_version_history(self, document_id, limit=50):
        """Get version history for a document.
        
        Returns list of version info dicts.
        """
        versions = self.search([
            ('document_id', '=', document_id)
        ], limit=limit, order='version_number desc')
        
        return [{
            'id': v.id,
            'version_number': v.version_number,
            'version_name': v.version_name or f'Version {v.version_number}',
            'file_size': v.file_size,
            'created_by': v.created_by.name,
            'created_by_avatar': f'/web/image/res.users/{v.created_by.id}/avatar_128',
            'create_date': v.create_date.isoformat() if v.create_date else None,
            'change_summary': v.change_summary,
            'is_pinned': v.is_pinned,
            'is_current': v.version_number == max(versions.mapped('version_number')),
        } for v in versions]


class OfficeDocumentComment(models.Model):
    """Comments on documents (Google Drive style).
    
    Features:
    - Threaded comments
    - @mentions
    - Resolve/reopen
    - Replies
    """
    _name = 'office.document.comment'
    _description = 'Document Comment'
    _order = 'create_date desc'

    document_id = fields.Many2one(
        'office.document',
        string='Document',
        required=True,
        ondelete='cascade',
        index=True,
    )
    
    # Comment content
    content = fields.Text(
        string='Comment',
        required=True,
    )
    
    # Threading
    parent_id = fields.Many2one(
        'office.document.comment',
        string='Reply To',
        ondelete='cascade',
    )
    reply_ids = fields.One2many(
        'office.document.comment',
        'parent_id',
        string='Replies',
    )
    
    # Resolution status
    is_resolved = fields.Boolean(
        string='Resolved',
        default=False,
    )
    resolved_by = fields.Many2one(
        'res.users',
        string='Resolved By',
    )
    resolved_date = fields.Datetime(
        string='Resolved Date',
    )
    
    # Author
    author_id = fields.Many2one(
        'res.users',
        string='Author',
        default=lambda self: self.env.user,
        required=True,
    )
    
    # Position in document (for contextual comments)
    anchor_text = fields.Char(
        string='Anchor Text',
        help='Text that this comment is attached to',
    )
    anchor_position = fields.Integer(
        string='Position',
        help='Character position in document',
    )
    
    # Mentions
    mentioned_user_ids = fields.Many2many(
        'res.users',
        'office_comment_mention_rel',
        'comment_id',
        'user_id',
        string='Mentioned Users',
    )

    @api.model
    def add_comment(self, document_id, content, parent_id=None, anchor_text=None):
        """Add a comment to a document."""
        # Extract mentions (@username)
        import re
        mentions = re.findall(r'@(\w+)', content)
        mentioned_users = self.env['res.users'].search([
            ('login', 'in', mentions)
        ])
        
        comment = self.create({
            'document_id': document_id,
            'content': content,
            'parent_id': parent_id,
            'anchor_text': anchor_text,
            'mentioned_user_ids': [(6, 0, mentioned_users.ids)],
        })
        
        # TODO: Send notifications to mentioned users
        
        return comment

    def resolve(self):
        """Mark comment as resolved."""
        self.ensure_one()
        self.write({
            'is_resolved': True,
            'resolved_by': self.env.user.id,
            'resolved_date': fields.Datetime.now(),
        })

    def reopen(self):
        """Reopen resolved comment."""
        self.ensure_one()
        self.write({
            'is_resolved': False,
            'resolved_by': False,
            'resolved_date': False,
        })

    @api.model
    def get_comments(self, document_id, include_resolved=False):
        """Get all comments for a document."""
        domain = [
            ('document_id', '=', document_id),
            ('parent_id', '=', False),  # Only top-level
        ]
        if not include_resolved:
            domain.append(('is_resolved', '=', False))
        
        comments = self.search(domain, order='create_date asc')
        
        def format_comment(c):
            return {
                'id': c.id,
                'content': c.content,
                'author_id': c.author_id.id,
                'author_name': c.author_id.name,
                'author_avatar': f'/web/image/res.users/{c.author_id.id}/avatar_128',
                'create_date': c.create_date.isoformat() if c.create_date else None,
                'is_resolved': c.is_resolved,
                'resolved_by': c.resolved_by.name if c.resolved_by else None,
                'anchor_text': c.anchor_text,
                'replies': [format_comment(r) for r in c.reply_ids],
            }
        
        return [format_comment(c) for c in comments]


class OfficeDocumentActivity(models.Model):
    """Activity/audit log for documents (Google Drive style).
    
    Tracks:
    - Views
    - Edits
    - Shares
    - Downloads
    - Permission changes
    """
    _name = 'office.document.activity'
    _description = 'Document Activity'
    _order = 'create_date desc'

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
    
    # Activity type
    activity_type = fields.Selection([
        ('create', 'Created'),
        ('view', 'Viewed'),
        ('edit', 'Edited'),
        ('download', 'Downloaded'),
        ('share', 'Shared'),
        ('unshare', 'Unshared'),
        ('move', 'Moved'),
        ('rename', 'Renamed'),
        ('trash', 'Moved to Trash'),
        ('restore', 'Restored'),
        ('delete', 'Deleted'),
        ('comment', 'Commented'),
        ('version', 'New Version'),
    ], string='Activity', required=True, index=True)
    
    # Who performed the action
    user_id = fields.Many2one(
        'res.users',
        string='User',
        default=lambda self: self.env.user,
        required=True,
        index=True,
    )
    
    # Details
    description = fields.Char(
        string='Description',
    )
    details = fields.Text(
        string='Details',
        help='JSON data with activity details',
    )
    
    # IP tracking (for security)
    ip_address = fields.Char(
        string='IP Address',
    )

    @api.model
    def log_activity(self, target_type, target_id, activity_type, description=None, details=None):
        """Log an activity."""
        vals = {
            'activity_type': activity_type,
            'user_id': self.env.user.id,
            'description': description,
            'details': details,
        }
        
        if target_type == 'document':
            vals['document_id'] = target_id
        else:
            vals['folder_id'] = target_id
        
        return self.create(vals)

    @api.model
    def get_activity_log(self, target_type, target_id, limit=50):
        """Get activity log for a document or folder."""
        domain = []
        if target_type == 'document':
            domain.append(('document_id', '=', target_id))
        else:
            domain.append(('folder_id', '=', target_id))
        
        activities = self.search(domain, limit=limit)
        
        return [{
            'id': a.id,
            'type': a.activity_type,
            'user_id': a.user_id.id,
            'user_name': a.user_id.name,
            'user_avatar': f'/web/image/res.users/{a.user_id.id}/avatar_128',
            'description': a.description,
            'create_date': a.create_date.isoformat() if a.create_date else None,
        } for a in activities]
