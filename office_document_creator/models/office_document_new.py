# -*- coding: utf-8 -*-
# Copyright 2025 Odoo Community
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""
Office Document Model - Enterprise Document Management System

This module provides Google Drive-like document management with:
- Support for ALL file types (images, videos, audio, code, archives, etc.)
- Native preview for 100+ file types
- Version history
- Comprehensive sharing
- Activity tracking
- Large file support (up to 10GB)
"""

import base64
import hashlib
import logging
import mimetypes
import os
import secrets
import uuid
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError
from odoo.modules.module import get_module_resource

_logger = logging.getLogger(__name__)

# =============================================================================
# FILE TYPE CONFIGURATION
# =============================================================================

# Maximum file size (10GB)
MAX_FILE_SIZE = 10 * 1024 * 1024 * 1024  # 10GB in bytes

# File categories with extensions and preview methods
FILE_CATEGORIES = {
    'image': {
        'extensions': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico', '.tiff', '.tif', '.heic', '.heif', '.raw', '.psd', '.ai'],
        'mimetypes': ['image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp', 'image/svg+xml', 'image/x-icon', 'image/tiff', 'image/heic', 'image/heif'],
        'preview': 'image',
        'icon': 'fa-file-image-o',
        'color': '#4285F4',
    },
    'video': {
        'extensions': ['.mp4', '.webm', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.m4v', '.mpeg', '.mpg', '.3gp', '.ogv'],
        'mimetypes': ['video/mp4', 'video/webm', 'video/quicktime', 'video/x-msvideo', 'video/x-matroska', 'video/x-ms-wmv', 'video/x-flv', 'video/mpeg', 'video/ogg'],
        'preview': 'video',
        'icon': 'fa-file-video-o',
        'color': '#EA4335',
    },
    'audio': {
        'extensions': ['.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a', '.wma', '.opus', '.aiff', '.mid', '.midi'],
        'mimetypes': ['audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/flac', 'audio/aac', 'audio/mp4', 'audio/x-ms-wma', 'audio/opus', 'audio/aiff', 'audio/midi'],
        'preview': 'audio',
        'icon': 'fa-file-audio-o',
        'color': '#9C27B0',
    },
    'pdf': {
        'extensions': ['.pdf'],
        'mimetypes': ['application/pdf'],
        'preview': 'pdf',
        'icon': 'fa-file-pdf-o',
        'color': '#E74C3C',
    },
    'word': {
        'extensions': ['.doc', '.docx', '.odt', '.rtf', '.dot', '.dotx'],
        'mimetypes': ['application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/vnd.oasis.opendocument.text', 'application/rtf'],
        'preview': 'office',
        'icon': 'fa-file-word-o',
        'color': '#2B5797',
    },
    'excel': {
        'extensions': ['.xls', '.xlsx', '.ods', '.csv', '.tsv', '.xlsm', '.xltx'],
        'mimetypes': ['application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.oasis.opendocument.spreadsheet', 'text/csv', 'text/tab-separated-values'],
        'preview': 'office',
        'icon': 'fa-file-excel-o',
        'color': '#217346',
    },
    'powerpoint': {
        'extensions': ['.ppt', '.pptx', '.odp', '.pps', '.ppsx', '.potx'],
        'mimetypes': ['application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation', 'application/vnd.oasis.opendocument.presentation'],
        'preview': 'office',
        'icon': 'fa-file-powerpoint-o',
        'color': '#D24726',
    },
    'code': {
        'extensions': [
            '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h', '.hpp',
            '.cs', '.go', '.rb', '.php', '.swift', '.kt', '.rs', '.scala', '.r',
            '.css', '.scss', '.less', '.sass', '.html', '.htm', '.xml', '.json',
            '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf', '.env',
            '.sql', '.sh', '.bash', '.zsh', '.ps1', '.bat', '.cmd',
            '.md', '.markdown', '.rst', '.tex', '.vue', '.svelte',
            '.dockerfile', '.gitignore', '.editorconfig', '.prettierrc',
        ],
        'mimetypes': ['text/x-python', 'application/javascript', 'text/typescript', 'text/x-java', 'text/x-c', 'text/html', 'application/json', 'text/yaml', 'application/xml', 'text/x-sql', 'text/x-shellscript', 'text/markdown'],
        'preview': 'code',
        'icon': 'fa-file-code-o',
        'color': '#607D8B',
    },
    'text': {
        'extensions': ['.txt', '.log', '.nfo', '.readme'],
        'mimetypes': ['text/plain'],
        'preview': 'text',
        'icon': 'fa-file-text-o',
        'color': '#7F8C8D',
    },
    'archive': {
        'extensions': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.tgz', '.tar.gz', '.tar.bz2'],
        'mimetypes': ['application/zip', 'application/x-rar-compressed', 'application/x-7z-compressed', 'application/x-tar', 'application/gzip', 'application/x-bzip2'],
        'preview': 'archive',
        'icon': 'fa-file-archive-o',
        'color': '#795548',
    },
    'ebook': {
        'extensions': ['.epub', '.mobi', '.azw', '.azw3', '.fb2'],
        'mimetypes': ['application/epub+zip', 'application/x-mobipocket-ebook'],
        'preview': 'ebook',
        'icon': 'fa-book',
        'color': '#8BC34A',
    },
    'font': {
        'extensions': ['.ttf', '.otf', '.woff', '.woff2', '.eot'],
        'mimetypes': ['font/ttf', 'font/otf', 'font/woff', 'font/woff2'],
        'preview': 'font',
        'icon': 'fa-font',
        'color': '#FF5722',
    },
    'design': {
        'extensions': ['.sketch', '.fig', '.xd', '.afdesign', '.afphoto'],
        'mimetypes': [],
        'preview': 'none',
        'icon': 'fa-paint-brush',
        'color': '#E91E63',
    },
    'cad': {
        'extensions': ['.dwg', '.dxf', '.stl', '.obj', '.fbx', '.blend', '.3ds', '.dae'],
        'mimetypes': [],
        'preview': '3d',
        'icon': 'fa-cube',
        'color': '#00BCD4',
    },
    'executable': {
        'extensions': ['.exe', '.msi', '.app', '.dmg', '.deb', '.rpm', '.apk', '.ipa'],
        'mimetypes': ['application/x-executable', 'application/x-msi', 'application/vnd.android.package-archive'],
        'preview': 'none',
        'icon': 'fa-cog',
        'color': '#9E9E9E',
    },
    'other': {
        'extensions': [],
        'mimetypes': [],
        'preview': 'none',
        'icon': 'fa-file-o',
        'color': '#9E9E9E',
    },
}

# Template files for new document creation
TEMPLATE_MAP = {
    'word': ('blank.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.docx'),
    'excel': ('blank.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', '.xlsx'),
    'powerpoint': ('blank.pptx', 'application/vnd.openxmlformats-officedocument.presentationml.presentation', '.pptx'),
    'text': ('blank.txt', 'text/plain', '.txt'),
}

# Language mapping for code syntax highlighting (Monaco Editor)
CODE_LANGUAGES = {
    '.py': 'python',
    '.js': 'javascript',
    '.ts': 'typescript',
    '.jsx': 'javascript',
    '.tsx': 'typescript',
    '.java': 'java',
    '.cpp': 'cpp',
    '.c': 'c',
    '.h': 'c',
    '.hpp': 'cpp',
    '.cs': 'csharp',
    '.go': 'go',
    '.rb': 'ruby',
    '.php': 'php',
    '.swift': 'swift',
    '.kt': 'kotlin',
    '.rs': 'rust',
    '.scala': 'scala',
    '.r': 'r',
    '.css': 'css',
    '.scss': 'scss',
    '.less': 'less',
    '.html': 'html',
    '.htm': 'html',
    '.xml': 'xml',
    '.json': 'json',
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.toml': 'toml',
    '.ini': 'ini',
    '.sql': 'sql',
    '.sh': 'shell',
    '.bash': 'shell',
    '.zsh': 'shell',
    '.ps1': 'powershell',
    '.md': 'markdown',
    '.markdown': 'markdown',
    '.vue': 'vue',
    '.dockerfile': 'dockerfile',
}


def get_file_category(filename, mimetype=None):
    """Determine file category from filename or mimetype."""
    ext = os.path.splitext(filename.lower())[1] if filename else ''
    
    for category, config in FILE_CATEGORIES.items():
        if ext in config['extensions']:
            return category
        if mimetype and mimetype in config['mimetypes']:
            return category
    
    return 'other'


def get_code_language(filename):
    """Get Monaco Editor language from filename."""
    ext = os.path.splitext(filename.lower())[1] if filename else ''
    return CODE_LANGUAGES.get(ext, 'plaintext')


def format_file_size(size_bytes):
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f'{size_bytes} B'
    elif size_bytes < 1024 * 1024:
        return f'{size_bytes / 1024:.1f} KB'
    elif size_bytes < 1024 * 1024 * 1024:
        return f'{size_bytes / (1024 * 1024):.1f} MB'
    else:
        return f'{size_bytes / (1024 * 1024 * 1024):.2f} GB'


# =============================================================================
# OFFICE DOCUMENT MODEL
# =============================================================================

class OfficeDocument(models.Model):
    _name = 'office.document'
    _description = 'Document'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'write_date desc'

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
    
    # File storage
    attachment_id = fields.Many2one(
        'ir.attachment',
        string='File',
        required=True,
        ondelete='cascade',
    )
    
    # File metadata
    file_size = fields.Integer(
        string='File Size (bytes)',
        compute='_compute_file_info',
        store=True,
    )
    file_size_human = fields.Char(
        string='Size',
        compute='_compute_file_info',
        store=True,
    )
    mimetype = fields.Char(
        string='MIME Type',
        compute='_compute_file_info',
        store=True,
    )
    file_extension = fields.Char(
        string='Extension',
        compute='_compute_file_info',
        store=True,
    )
    checksum = fields.Char(
        string='Checksum',
        compute='_compute_file_info',
        store=True,
        help='MD5 hash for deduplication',
    )
    
    # File categorization
    file_category = fields.Selection([
        ('image', 'Image'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('pdf', 'PDF'),
        ('word', 'Word Document'),
        ('excel', 'Spreadsheet'),
        ('powerpoint', 'Presentation'),
        ('code', 'Code'),
        ('text', 'Text'),
        ('archive', 'Archive'),
        ('ebook', 'E-Book'),
        ('font', 'Font'),
        ('design', 'Design'),
        ('cad', 'CAD/3D'),
        ('executable', 'Executable'),
        ('other', 'Other'),
    ], string='Category', compute='_compute_file_category', store=True, index=True)
    
    # Alias for backward compatibility with views
    document_type = fields.Selection([
        ('image', 'Image'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('pdf', 'PDF'),
        ('word', 'Word Document'),
        ('excel', 'Spreadsheet'),
        ('powerpoint', 'Presentation'),
        ('code', 'Code'),
        ('text', 'Text'),
        ('archive', 'Archive'),
        ('ebook', 'E-Book'),
        ('font', 'Font'),
        ('design', 'Design'),
        ('cad', 'CAD/3D'),
        ('executable', 'Executable'),
        ('other', 'Other'),
    ], string='Document Type', related='file_category', store=True, readonly=True)
    
    preview_type = fields.Selection([
        ('image', 'Image Viewer'),
        ('video', 'Video Player'),
        ('audio', 'Audio Player'),
        ('pdf', 'PDF Viewer'),
        ('office', 'Office Editor'),
        ('code', 'Code Editor'),
        ('text', 'Text Viewer'),
        ('archive', 'Archive Viewer'),
        ('ebook', 'E-Book Reader'),
        ('font', 'Font Preview'),
        ('3d', '3D Viewer'),
        ('none', 'No Preview'),
    ], string='Preview Type', compute='_compute_preview_type', store=True)
    
    code_language = fields.Char(
        string='Code Language',
        compute='_compute_code_language',
        help='Monaco Editor language ID',
    )
    
    # UI display
    icon = fields.Char(
        string='Icon',
        compute='_compute_display_info',
    )
    color = fields.Char(
        string='Color',
        compute='_compute_display_info',
    )
    thumbnail = fields.Binary(
        string='Thumbnail',
        attachment=True,
    )
    
    # =========================================================================
    # OWNERSHIP & ACCESS
    # =========================================================================
    
    owner_id = fields.Many2one(
        'res.users',
        string='Owner',
        default=lambda self: self.env.user,
        required=True,
        tracking=True,
        index=True,
    )
    
    # Individual access (linked model)
    access_ids = fields.One2many(
        'office.document.access',
        'document_id',
        string='Access Permissions',
    )
    access_count = fields.Integer(
        string='Shared With',
        compute='_compute_access_count',
    )
    
    # Legacy field for backward compatibility
    shared_user_ids = fields.Many2many(
        'res.users',
        'office_document_share_rel',
        'document_id',
        'user_id',
        string='Shared With (Legacy)',
    )
    
    # Share links
    share_link_ids = fields.One2many(
        'office.share.link',
        'document_id',
        string='Share Links',
    )
    has_public_link = fields.Boolean(
        string='Has Public Link',
        compute='_compute_has_public_link',
    )
    
    # Share link legacy fields for view compatibility
    share_link_active = fields.Boolean(
        string='Share Link Active',
        compute='_compute_share_link_info',
    )
    share_permission = fields.Selection([
        ('viewer', 'Viewer'),
        ('commenter', 'Commenter'),
        ('editor', 'Editor'),
    ], string='Link Permission', compute='_compute_share_link_info')
    share_link = fields.Char(
        string='Share Link',
        compute='_compute_share_link_info',
    )
    is_shared = fields.Boolean(
        string='Is Shared',
        compute='_compute_is_shared',
    )
    is_template = fields.Boolean(
        string='Is Template',
        default=False,
    )
    original_document_id = fields.Many2one(
        'office.document',
        string='Original Document',
        help='Reference to original document if this is a copy',
    )
    
    # =========================================================================
    # ORGANIZATION
    # =========================================================================
    
    folder_id = fields.Many2one(
        'office.folder',
        string='Folder',
        ondelete='set null',
        index=True,
    )
    
    is_starred = fields.Boolean(
        string='Starred',
        default=False,
        index=True,
    )
    
    tags = fields.Char(
        string='Tags',
        help='Comma-separated tags',
    )
    tag_ids = fields.Many2many(
        'office.document.tag',
        'office_document_tag_rel',
        'document_id',
        'tag_id',
        string='Tags',
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
    original_folder_id = fields.Many2one(
        'office.folder',
        string='Original Folder',
        help='Folder before moving to trash (for restore)',
    )
    
    # =========================================================================
    # VERSIONING
    # =========================================================================
    
    version_ids = fields.One2many(
        'office.document.version',
        'document_id',
        string='Versions',
    )
    version_count = fields.Integer(
        string='Version Count',
        compute='_compute_version_count',
    )
    current_version = fields.Integer(
        string='Current Version',
        default=1,
    )
    
    # =========================================================================
    # ACTIVITY TRACKING
    # =========================================================================
    
    # Note: activity_ids is inherited from mail.activity.mixin - do not override!
    # Using office_activity_ids for our custom activity log
    office_activity_ids = fields.One2many(
        'office.document.activity',
        'document_id',
        string='Activity Log',
    )
    
    last_accessed = fields.Datetime(
        string='Last Accessed',
        default=fields.Datetime.now,
        index=True,
    )
    access_count_total = fields.Integer(
        string='Total Views',
        default=0,
    )
    last_edited = fields.Datetime(
        string='Last Edited',
    )
    last_edited_by = fields.Many2one(
        'res.users',
        string='Last Edited By',
    )
    
    # =========================================================================
    # COMMENTS
    # =========================================================================
    
    comment_ids = fields.One2many(
        'office.document.comment',
        'document_id',
        string='Comments',
    )
    comment_count = fields.Integer(
        string='Comments',
        compute='_compute_comment_count',
    )
    
    # =========================================================================
    # COMPUTED FIELDS
    # =========================================================================
    
    @api.depends('attachment_id', 'attachment_id.file_size', 'attachment_id.mimetype', 'attachment_id.checksum')
    def _compute_file_info(self):
        for record in self:
            if record.attachment_id:
                record.file_size = record.attachment_id.file_size or 0
                record.file_size_human = format_file_size(record.file_size)
                record.mimetype = record.attachment_id.mimetype
                record.file_extension = os.path.splitext(record.attachment_id.name or '')[1].lower()
                record.checksum = record.attachment_id.checksum
            else:
                record.file_size = 0
                record.file_size_human = '0 B'
                record.mimetype = ''
                record.file_extension = ''
                record.checksum = ''

    @api.depends('name', 'mimetype')
    def _compute_file_category(self):
        for record in self:
            record.file_category = get_file_category(record.name, record.mimetype)

    @api.depends('file_category')
    def _compute_preview_type(self):
        for record in self:
            category = record.file_category
            if category and category in FILE_CATEGORIES:
                record.preview_type = FILE_CATEGORIES[category].get('preview', 'none')
            else:
                record.preview_type = 'none'

    @api.depends('name')
    def _compute_code_language(self):
        for record in self:
            record.code_language = get_code_language(record.name)

    @api.depends('file_category')
    def _compute_display_info(self):
        for record in self:
            category = record.file_category or 'other'
            config = FILE_CATEGORIES.get(category, FILE_CATEGORIES['other'])
            record.icon = config.get('icon', 'fa-file-o')
            record.color = config.get('color', '#9E9E9E')

    @api.depends('access_ids')
    def _compute_access_count(self):
        for record in self:
            record.access_count = len(record.access_ids)

    @api.depends('share_link_ids', 'share_link_ids.is_active')
    def _compute_has_public_link(self):
        for record in self:
            record.has_public_link = any(link.is_active for link in record.share_link_ids)

    @api.depends('share_link_ids', 'share_link_ids.is_active', 'share_link_ids.permission', 'share_link_ids.token')
    def _compute_share_link_info(self):
        """Compute share link info for form view display."""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        for record in self:
            active_link = record.share_link_ids.filtered(lambda l: l.is_active)[:1]
            if active_link:
                record.share_link_active = True
                record.share_permission = active_link.permission
                record.share_link = f"{base_url}/office/share/{active_link.token}"
            else:
                record.share_link_active = False
                record.share_permission = False
                record.share_link = False

    @api.depends('access_ids', 'share_link_ids')
    def _compute_is_shared(self):
        """Compute if document is shared with anyone."""
        for record in self:
            record.is_shared = bool(record.access_ids or record.share_link_ids.filtered(lambda l: l.is_active))

    @api.depends('version_ids')
    def _compute_version_count(self):
        for record in self:
            record.version_count = len(record.version_ids)

    @api.depends('comment_ids')
    def _compute_comment_count(self):
        for record in self:
            record.comment_count = len(record.comment_ids.filtered(lambda c: not c.is_resolved))

    # =========================================================================
    # CONSTRAINTS
    # =========================================================================
    
    @api.constrains('name')
    def _check_name(self):
        for record in self:
            if not record.name or not record.name.strip():
                raise ValidationError(_('Document name cannot be empty.'))
            if len(record.name) > 255:
                raise ValidationError(_('Document name cannot exceed 255 characters.'))

    @api.constrains('file_size')
    def _check_file_size(self):
        for record in self:
            if record.file_size > MAX_FILE_SIZE:
                raise ValidationError(_(
                    'File size exceeds maximum limit of %s.'
                ) % format_file_size(MAX_FILE_SIZE))

    # =========================================================================
    # CRUD OVERRIDES
    # =========================================================================
    
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            # Log creation activity
            self.env['office.document.activity'].log_activity(
                'document', record.id, 'create',
                description=f'Created document "{record.name}"'
            )
            # Create initial version
            if record.attachment_id:
                self.env['office.document.version'].create_version(
                    record.id,
                    name='Initial version',
                    summary='Document created'
                )
        return records

    def write(self, vals):
        # Track content changes for versioning
        if 'attachment_id' in vals:
            for record in self:
                old_checksum = record.checksum
                result = super(OfficeDocument, record).write(vals)
                if record.checksum != old_checksum:
                    # Content changed, create new version
                    self.env['office.document.version'].create_version(
                        record.id,
                        summary='Document updated'
                    )
                    record.last_edited = fields.Datetime.now()
                    record.last_edited_by = self.env.user.id
                    record.current_version += 1
            return result
        return super().write(vals)

    def unlink(self):
        # Log deletion and cleanup
        for record in self:
            self.env['office.document.activity'].log_activity(
                'document', record.id, 'delete',
                description=f'Permanently deleted "{record.name}"'
            )
        
        # Delete attachments
        attachments = self.mapped('attachment_id')
        result = super().unlink()
        attachments.unlink()
        return result

    # =========================================================================
    # DOCUMENT CREATION
    # =========================================================================
    
    @api.model
    def create_document_from_template(self, doc_type, folder_id=False, name=None):
        """Create a new document from a blank template.
        
        Args:
            doc_type: 'word', 'excel', 'powerpoint', or 'text'
            folder_id: Optional folder ID
            name: Optional document name
            
        Returns:
            Dict with document_id, name, attachment_id
        """
        if doc_type not in TEMPLATE_MAP:
            raise UserError(_('Invalid document type: %s') % doc_type)
        
        template_file, mimetype, file_ext = TEMPLATE_MAP[doc_type]
        
        # Get template file
        template_path = get_module_resource(
            'office_document_creator', 'static', 'templates', template_file
        )
        
        if not template_path or not os.path.exists(template_path):
            raise UserError(_('Template file not found: %s') % template_file)
        
        with open(template_path, 'rb') as f:
            file_data = f.read()
        
        # Generate unique name
        if not name:
            doc_names = {
                'word': _('Untitled Document'),
                'excel': _('Untitled Spreadsheet'),
                'powerpoint': _('Untitled Presentation'),
                'text': _('Untitled Text'),
            }
            base_name = doc_names.get(doc_type, _('Untitled'))
            name = self._generate_unique_name(base_name, folder_id)
        
        # Create attachment
        attachment = self.env['ir.attachment'].create({
            'name': f"{name}{file_ext}",
            'datas': base64.b64encode(file_data),
            'mimetype': mimetype,
            'res_model': 'office.document',
            'public': True,
        })
        
        # Create document
        document = self.create({
            'name': name,
            'attachment_id': attachment.id,
            'owner_id': self.env.user.id,
            'folder_id': folder_id or False,
        })
        
        # Link attachment
        attachment.res_id = document.id
        
        _logger.info(f'Created new {doc_type} document: {name} (ID: {document.id})')
        
        return {
            'document_id': document.id,
            'name': name,
            'attachment_id': attachment.id,
        }

    def _generate_unique_name(self, base_name, folder_id=False):
        """Generate a unique document name."""
        name = base_name
        counter = 0
        
        while self.search([
            ('name', '=', name),
            ('owner_id', '=', self.env.user.id),
            ('folder_id', '=', folder_id),
            ('is_trashed', '=', False),
        ], limit=1):
            counter += 1
            name = f'{base_name} ({counter})'
        
        return name

    # =========================================================================
    # FILE UPLOAD
    # =========================================================================
    
    @api.model
    def upload_document(self, filename, file_data, folder_id=False, create_version=True):
        """Upload a document file.
        
        Args:
            filename: Original filename
            file_data: Base64 encoded file data
            folder_id: Optional folder ID
            create_version: Whether to create initial version
            
        Returns:
            Dict with document info
        """
        # Decode if string
        if isinstance(file_data, str):
            try:
                file_data = base64.b64decode(file_data)
            except Exception:
                raise UserError(_('Invalid file data'))
        
        # Validate file size
        if len(file_data) > MAX_FILE_SIZE:
            raise ValidationError(_(
                'File size (%s) exceeds maximum limit of %s.'
            ) % (format_file_size(len(file_data)), format_file_size(MAX_FILE_SIZE)))
        
        # Determine mimetype
        mimetype, _ = mimetypes.guess_type(filename)
        if not mimetype:
            mimetype = 'application/octet-stream'
        
        # Get file extension
        base_name, file_ext = os.path.splitext(filename)
        if not file_ext:
            file_ext = ''
        
        # Generate unique name
        name = self._generate_unique_name(base_name, folder_id)
        
        # Create attachment
        attachment = self.env['ir.attachment'].create({
            'name': f"{name}{file_ext}",
            'datas': base64.b64encode(file_data) if isinstance(file_data, bytes) else file_data,
            'mimetype': mimetype,
            'res_model': 'office.document',
            'public': True,  # Required for OnlyOffice
        })
        
        # Create document
        document = self.create({
            'name': name,
            'attachment_id': attachment.id,
            'owner_id': self.env.user.id,
            'folder_id': folder_id or False,
        })
        
        # Link attachment
        attachment.res_id = document.id
        
        _logger.info(f'Uploaded document: {name} ({format_file_size(len(file_data))})')
        
        return {
            'document_id': document.id,
            'name': name,
            'file_category': document.file_category,
            'preview_type': document.preview_type,
        }

    # =========================================================================
    # DOCUMENT ACTIONS
    # =========================================================================
    
    def action_open_editor(self):
        """Open document in appropriate editor/viewer."""
        self.ensure_one()
        
        if not self.attachment_id:
            raise UserError(_('No file attached to this document.'))
        
        # Track access
        self.write({
            'last_accessed': fields.Datetime.now(),
            'access_count_total': self.access_count_total + 1,
        })
        
        # Log activity
        self.env['office.document.activity'].log_activity(
            'document', self.id, 'view',
            description=f'Viewed document'
        )
        
        # Route based on preview type
        if self.preview_type == 'office':
            # Open in OnlyOffice
            return {
                'type': 'ir.actions.act_url',
                'url': f'/onlyoffice/editor/{self.attachment_id.id}',
                'target': 'new',
            }
        elif self.preview_type in ('image', 'video', 'audio', 'pdf', 'code', 'text'):
            # Open in native preview
            return {
                'type': 'ir.actions.act_url',
                'url': f'/office/preview/{self.id}',
                'target': 'new',
            }
        else:
            # Download
            return self.action_download()

    def action_download(self):
        """Download the document."""
        self.ensure_one()
        
        if not self.attachment_id:
            raise UserError(_('No file attached to this document.'))
        
        # Log activity
        self.env['office.document.activity'].log_activity(
            'document', self.id, 'download',
            description='Downloaded document'
        )
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.attachment_id.id}?download=true',
            'target': 'self',
        }

    def save_content(self, content):
        """Save text content to document attachment.
        
        Used by Monaco Editor for code files and text editor.
        
        Args:
            content: String content to save
            
        Returns:
            True on success
        """
        self.ensure_one()
        
        if not self.attachment_id:
            raise UserError(_('No file attached to this document.'))
        
        # Check ownership
        if self.owner_id.id != self.env.user.id:
            # Check if user has editor access
            access = self.env['office.document.access'].search([
                ('document_id', '=', self.id),
                ('user_id', '=', self.env.user.id),
                ('permission', '=', 'editor'),
            ], limit=1)
            if not access:
                raise AccessError(_('You do not have permission to edit this document.'))
        
        # Encode content
        encoded = base64.b64encode(content.encode('utf-8'))
        
        # Store old checksum for version detection
        old_checksum = self.checksum
        
        # Update attachment (with context to skip auto-versioning if needed)
        self.attachment_id.with_context(skip_auto_version=True).write({
            'datas': encoded,
        })
        
        # Update metadata
        self.write({
            'last_edited': fields.Datetime.now(),
            'last_edited_by': self.env.user.id,
        })
        
        # Create version if content changed
        new_checksum = self.attachment_id.checksum
        if old_checksum != new_checksum:
            self.env['office.document.version'].create_version(
                self.id,
                summary='Content updated via editor'
            )
            self.current_version += 1
        
        # Log activity
        self.env['office.document.activity'].log_activity(
            'document', self.id, 'edit',
            description='Edited document content'
        )
        
        _logger.info(f'Saved content for document: {self.name} (ID: {self.id})')
        
        return True

    def action_duplicate(self):
        """Create a copy of the document."""
        self.ensure_one()
        
        # Copy attachment
        new_name = self._generate_unique_name(f'{self.name} (copy)', self.folder_id.id if self.folder_id else False)
        
        new_attachment = self.attachment_id.copy({
            'name': f"{new_name}{self.file_extension}",
        })
        
        # Create new document
        new_doc = self.copy({
            'name': new_name,
            'attachment_id': new_attachment.id,
            'is_starred': False,
            'access_ids': [],
            'share_link_ids': [],
        })
        
        new_attachment.res_id = new_doc.id
        
        _logger.info(f'Duplicated document: {self.name} -> {new_name}')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Document duplicated as "%s"') % new_name,
                'type': 'success',
            }
        }

    def action_rename(self, new_name):
        """Rename the document."""
        self.ensure_one()
        
        new_name = (new_name or '').strip()
        if not new_name:
            raise ValidationError(_('Name cannot be empty.'))
        
        old_name = self.name
        
        # Check for duplicates
        existing = self.search([
            ('id', '!=', self.id),
            ('name', '=', new_name),
            ('owner_id', '=', self.owner_id.id),
            ('folder_id', '=', self.folder_id.id if self.folder_id else False),
            ('is_trashed', '=', False),
        ], limit=1)
        
        if existing:
            raise ValidationError(_('A document with this name already exists.'))
        
        # Update attachment name
        if self.attachment_id:
            self.attachment_id.sudo().write({
                'name': f"{new_name}{self.file_extension}"
            })
        
        self.write({'name': new_name})
        
        # Log activity
        self.env['office.document.activity'].log_activity(
            'document', self.id, 'rename',
            description=f'Renamed from "{old_name}" to "{new_name}"'
        )
        
        return True

    def action_toggle_star(self):
        """Toggle starred status."""
        self.ensure_one()
        self.is_starred = not self.is_starred
        return {'is_starred': self.is_starred}

    def action_move_to_trash(self):
        """Move document to trash."""
        self.ensure_one()
        
        self.write({
            'is_trashed': True,
            'trashed_date': fields.Datetime.now(),
            'trashed_by': self.env.user.id,
            'original_folder_id': self.folder_id.id if self.folder_id else False,
            'folder_id': False,
        })
        
        # Log activity
        self.env['office.document.activity'].log_activity(
            'document', self.id, 'trash',
            description='Moved to trash'
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Moved to Trash'),
                'message': _('Document will be permanently deleted in 30 days.'),
                'type': 'warning',
            }
        }

    def action_restore_from_trash(self):
        """Restore document from trash."""
        self.ensure_one()
        
        self.write({
            'is_trashed': False,
            'trashed_date': False,
            'trashed_by': False,
            'folder_id': self.original_folder_id.id if self.original_folder_id else False,
            'original_folder_id': False,
        })
        
        # Log activity
        self.env['office.document.activity'].log_activity(
            'document', self.id, 'restore',
            description='Restored from trash'
        )
        
        return True

    def action_permanent_delete(self):
        """Permanently delete document."""
        self.ensure_one()
        self.unlink()
        return {'type': 'ir.actions.act_window_close'}

    # =========================================================================
    # SHARING
    # =========================================================================
    
    def action_share(self):
        """Open share dialog."""
        self.ensure_one()
        return {
            'name': _('Share "%s"') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'office.document.share.wizard',
            'view_mode': 'form',
            'views': [[False, 'form']],
            'target': 'new',
            'context': {'default_document_id': self.id},
        }

    def action_generate_share_link(self):
        """Generate a public share link for this document."""
        self.ensure_one()
        ShareLink = self.env['office.share.link']
        
        # Deactivate existing links
        existing = ShareLink.search([
            ('document_id', '=', self.id),
            ('is_active', '=', True),
        ])
        existing.write({'is_active': False})
        
        # Create new link
        link = ShareLink.create_share_link('document', self.id)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Share Link Created'),
                'message': _('Public share link has been generated.'),
                'type': 'success',
            }
        }

    def action_disable_share_link(self):
        """Disable all public share links for this document."""
        self.ensure_one()
        ShareLink = self.env['office.share.link']
        
        existing = ShareLink.search([
            ('document_id', '=', self.id),
            ('is_active', '=', True),
        ])
        existing.write({'is_active': False})
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Share Link Disabled'),
                'message': _('Public share link has been disabled.'),
                'type': 'warning',
            }
        }

    def action_move_to_folder(self, folder_id=False):
        """Move document to a folder."""
        self.ensure_one()
        if folder_id:
            self.write({'folder_id': folder_id})
            self.env['office.document.activity'].log_activity(
                document_id=self.id,
                activity_type='move',
                description=f'Moved to folder',
            )
        return True

    def get_access_list(self):
        """Get list of all users with access to this document."""
        self.ensure_one()
        return self.env['office.document.access'].get_access_list('document', self.id)

    def grant_access(self, user_id, permission='viewer', notify=True):
        """Grant access to a user."""
        self.ensure_one()
        return self.env['office.document.access'].grant_access(
            'document', self.id, user_id, permission, notify
        )

    def revoke_access(self, user_id):
        """Revoke access from a user."""
        self.ensure_one()
        return self.env['office.document.access'].revoke_access(
            'document', self.id, user_id
        )

    def get_share_link_info(self):
        """Get public link info - creates link if doesn't exist."""
        self.ensure_one()
        
        if self.owner_id.id != self.env.user.id:
            raise AccessError(_('Only the owner can manage share links.'))
        
        link = self.env['office.share.link'].get_link_for_target('document', self.id)
        
        # Create link if doesn't exist (inactive by default)
        if not link:
            link = self.env['office.share.link'].create_link(
                'document', self.id, 'viewer'
            )
            link.write({'is_active': False})
        
        return {
            'is_active': link.is_active,
            'permission': link.permission,
            'url': link.get_share_url(),
            'token': link.token,
            'allow_download': link.allow_download,
            'has_expiry': link.has_expiry,
            'expiry_date': link.expiry_date.isoformat() if link.expiry_date else None,
            'view_count': link.view_count,
        }

    def update_share_link(self, permission='viewer', active=True, 
                          allow_download=True, expiry_days=None, regenerate=False):
        """Update or create share link."""
        self.ensure_one()
        
        if self.owner_id.id != self.env.user.id:
            raise AccessError(_('Only the owner can manage share links.'))
        
        link = self.env['office.share.link'].get_link_for_target('document', self.id)
        
        if link:
            vals = {
                'permission': permission,
                'is_active': active,
                'allow_download': allow_download,
            }
            
            if regenerate:
                vals['token'] = secrets.token_urlsafe(32)
            
            if expiry_days:
                vals['has_expiry'] = True
                vals['expiry_date'] = fields.Datetime.now() + timedelta(days=expiry_days)
            elif expiry_days == 0:
                vals['has_expiry'] = False
                vals['expiry_date'] = False
            
            link.write(vals)
        else:
            link = self.env['office.share.link'].create_link(
                'document', self.id, permission,
                expiry_days=expiry_days, allow_download=allow_download
            )
        
        return self.get_share_link_info()

    # =========================================================================
    # FOLDER OPERATIONS
    # =========================================================================
    
    @api.model
    def move_document(self, document_id, target_folder_id=False):
        """Move document to a folder."""
        doc = self.browse(document_id)
        if not doc.exists():
            raise UserError(_('Document not found'))
        
        if doc.owner_id.id != self.env.user.id:
            raise AccessError(_('Only the owner can move this document.'))
        
        old_folder = doc.folder_id.name if doc.folder_id else 'My Drive'
        doc.folder_id = target_folder_id or False
        new_folder = doc.folder_id.name if doc.folder_id else 'My Drive'
        
        # Log activity
        self.env['office.document.activity'].log_activity(
            'document', doc.id, 'move',
            description=f'Moved from "{old_folder}" to "{new_folder}"'
        )
        
        return True

    # =========================================================================
    # QUERY METHODS (Optimized for dashboard)
    # =========================================================================
    
    @api.model
    def get_dashboard_data(self, folder_id=False, limit=50):
        """Get all dashboard data in a single call (optimized)."""
        user_id = self.env.user.id
        
        # Build folder context
        folder_id = self._normalize_folder_id(folder_id)
        
        # Get documents for the current folder
        documents = self._get_folder_documents(folder_id, limit=100)
        
        # Get subfolders for the current folder - ONLY owned by current user
        folder_domain = [
            ('parent_id', '=', folder_id if folder_id else False),
            ('owner_id', '=', user_id),
            ('is_trashed', '=', False),
        ]
        folders = self.env['office.folder'].search(folder_domain, order='name')
        folders_data = [{
            'id': f.id,
            'name': f.name,
            'color': f.color or '#9E9E9E',
            'document_count': f.document_count,
            'subfolder_count': f.subfolder_count,
            'is_starred': f.is_starred,
            'access_count': len(f.access_ids),
            'owner_name': f.owner_id.name,
            'write_date': f.write_date.isoformat() if f.write_date else '',
        } for f in folders]
        
        # Get data
        return {
            'documents': documents,
            'folders': folders_data,
            'breadcrumb': self._get_folder_path(folder_id),
            'folder_tree': self.env['office.folder'].get_folder_tree(False),
            'storage_used': self._get_storage_stats().get('used', 0),
            'current_folder_id': folder_id,
        }

    def get_dashboard_data_by_filter(self, filter):
        """Get dashboard data for filtered views (recent, starred, shared, trash)."""
        if filter == 'recent':
            documents = self._get_recent_documents(limit=50)
            folders = []
        elif filter == 'starred':
            documents = self._get_starred_documents(limit=50)
            # Get starred folders too
            starred_folders = self.env['office.folder'].search([
                ('is_starred', '=', True),
                ('is_trashed', '=', False),
            ])
            folders = [{
                'id': f.id,
                'name': f.name,
                'color': f.color or '#9E9E9E',
                'document_count': f.document_count,
                'is_starred': True,
                'owner_name': f.owner_id.name,
                'write_date': f.write_date.isoformat() if f.write_date else '',
            } for f in starred_folders]
        elif filter == 'shared':
            documents = self._get_shared_with_me(limit=50)
            # Get shared folders (use sudo to bypass security rules)
            access_records = self.env['office.document.access'].sudo().search([
                ('user_id', '=', self.env.user.id),
                ('folder_id', '!=', False),
            ])
            shared_folder_ids = access_records.mapped('folder_id').ids
            
            # Also check legacy shared_user_ids on folders
            legacy_shared_folders = self.env['office.folder'].sudo().search([
                ('shared_user_ids', 'in', [self.env.user.id]),
                ('owner_id', '!=', self.env.user.id),
                ('is_trashed', '=', False),
            ])
            all_folder_ids = list(set(shared_folder_ids + legacy_shared_folders.ids))
            
            shared_folders = self.env['office.folder'].sudo().browse(all_folder_ids).filtered(lambda f: not f.is_trashed)
            folders = [{
                'id': f.id,
                'name': f.name,
                'color': f.color or '#9E9E9E',
                'document_count': f.document_count,
                'owner_name': f.owner_id.name,
                'write_date': f.write_date.isoformat() if f.write_date else '',
            } for f in shared_folders]
        elif filter == 'trash':
            # Get trashed documents
            docs = self.search([
                ('owner_id', '=', self.env.user.id),
                ('is_trashed', '=', True),
            ], order='write_date desc', limit=100)
            documents = self._format_documents(docs)
            # Get trashed folders
            trashed_folders = self.env['office.folder'].search([
                ('owner_id', '=', self.env.user.id),
                ('is_trashed', '=', True),
            ], order='write_date desc')
            folders = [{
                'id': f.id,
                'name': f.name,
                'color': f.color or '#9E9E9E',
                'document_count': f.document_count,
                'owner_name': f.owner_id.name,
                'write_date': f.write_date.isoformat() if f.write_date else '',
            } for f in trashed_folders]
        else:
            documents = []
            folders = []
        
        return {
            'documents': documents,
            'folders': folders,
            'breadcrumb': [],
            'folder_tree': self.env['office.folder'].get_folder_tree(False),
            'storage_used': self._get_storage_stats().get('used', 0),
        }

    def _normalize_folder_id(self, folder_id):
        """Normalize folder_id from various input formats."""
        if not folder_id:
            return False
        if isinstance(folder_id, dict):
            folder_id = folder_id.get('id', False)
        elif isinstance(folder_id, (list, tuple)):
            folder_id = folder_id[0] if folder_id else False
        try:
            return int(folder_id) if folder_id else False
        except (ValueError, TypeError):
            return False

    def _get_recent_documents(self, limit=20):
        """Get recently accessed documents."""
        docs = self.search([
            ('owner_id', '=', self.env.user.id),
            ('is_trashed', '=', False),
        ], order='last_accessed desc', limit=limit)
        
        return self._format_documents(docs)

    def _get_starred_documents(self, limit=50):
        """Get starred documents."""
        docs = self.search([
            ('owner_id', '=', self.env.user.id),
            ('is_starred', '=', True),
            ('is_trashed', '=', False),
        ], order='name', limit=limit)
        
        return self._format_documents(docs)

    def _get_shared_with_me(self, limit=50):
        """Get documents shared with current user."""
        # Get from access records (use sudo to bypass rules when fetching access list)
        access_records = self.env['office.document.access'].sudo().search([
            ('user_id', '=', self.env.user.id),
            ('document_id', '!=', False),
        ], limit=limit)
        
        # Get document IDs that user has access to
        doc_ids = access_records.mapped('document_id').ids
        
        # Also check shared_user_ids (legacy method)
        legacy_shared = self.sudo().search([
            ('shared_user_ids', 'in', [self.env.user.id]),
            ('owner_id', '!=', self.env.user.id),
            ('is_trashed', '=', False),
        ], limit=limit)
        
        # Combine both
        all_doc_ids = list(set(doc_ids + legacy_shared.ids))
        
        # Now read documents with sudo and format
        docs = self.sudo().browse(all_doc_ids).filtered(
            lambda d: not d.is_trashed
        )
        
        return self._format_documents(docs, include_owner=True)

    def _get_folder_documents(self, folder_id, limit=100):
        """Get documents in a specific folder."""
        domain = [
            ('owner_id', '=', self.env.user.id),
            ('is_trashed', '=', False),
            ('folder_id', '=', folder_id if folder_id else False),
        ]
        
        docs = self.search(domain, order='write_date desc', limit=limit)
        return self._format_documents(docs)

    def _get_folder_path(self, folder_id):
        """Get breadcrumb path for folder."""
        if not folder_id:
            return []
        return self.env['office.folder'].get_folder_path(folder_id)

    def _get_storage_stats(self):
        """Get storage statistics."""
        docs = self.search([
            ('owner_id', '=', self.env.user.id),
            ('is_trashed', '=', False),
        ])
        
        total_size = sum(docs.mapped('file_size'))
        
        # Count by category
        by_category = {}
        for doc in docs:
            cat = doc.file_category or 'other'
            by_category[cat] = by_category.get(cat, 0) + 1
        
        return {
            'total_size': total_size,
            'total_size_human': format_file_size(total_size),
            'document_count': len(docs),
            'by_category': by_category,
        }

    def _format_documents(self, docs, include_owner=False):
        """Format documents for JSON response."""
        result = []
        for doc in docs:
            data = {
                'id': doc.id,
                'name': doc.name,
                'file_category': doc.file_category,
                'preview_type': doc.preview_type,
                'icon': doc.icon,
                'color': doc.color,
                'file_size': doc.file_size,
                'file_size_human': doc.file_size_human,
                'mimetype': doc.mimetype,
                'is_starred': doc.is_starred,
                'write_date': doc.write_date.isoformat() if doc.write_date else None,
                'folder_id': doc.folder_id.id if doc.folder_id else False,
                'folder_name': doc.folder_id.name if doc.folder_id else None,
                'has_public_link': doc.has_public_link,
                'access_count': doc.access_count,
                'attachment_id': doc.attachment_id.id,
            }
            
            if include_owner:
                data['owner_id'] = doc.owner_id.id
                data['owner_name'] = doc.owner_id.name
            
            result.append(data)
        
        return result

    # Backward compatibility methods
    @api.model
    def get_recent_documents(self, limit=20):
        return self._get_recent_documents(limit)

    @api.model
    def get_starred_documents(self):
        return self._get_starred_documents()

    @api.model
    def get_shared_with_me(self):
        return self._get_shared_with_me()

    @api.model
    def get_trash_documents(self):
        """Get documents in trash."""
        docs = self.search([
            ('owner_id', '=', self.env.user.id),
            ('is_trashed', '=', True),
        ], order='trashed_date desc')
        
        return self._format_documents(docs)

    @api.model
    def get_documents_in_folder(self, folder_id=False):
        return self._get_folder_documents(self._normalize_folder_id(folder_id), 100)

    @api.model
    def get_storage_stats(self):
        return self._get_storage_stats()

    @api.model
    def empty_trash(self):
        """Empty trash (permanent delete all)."""
        trashed = self.search([
            ('owner_id', '=', self.env.user.id),
            ('is_trashed', '=', True),
        ])
        count = len(trashed)
        trashed.unlink()
        return count

    @api.model
    def auto_delete_old_trash(self):
        """Cron: Auto-delete documents in trash for more than 30 days."""
        cutoff = fields.Datetime.now() - timedelta(days=30)
        old_trash = self.search([
            ('is_trashed', '=', True),
            ('trashed_date', '<', cutoff),
        ])
        count = len(old_trash)
        old_trash.unlink()
        _logger.info(f'Auto-deleted {count} documents from trash (>30 days)')
        return count

    # =========================================================================
    # SEARCH
    # =========================================================================
    
    @api.model
    def search_documents(self, query, filters=None):
        """Advanced search with filters.
        
        Args:
            query: Search text
            filters: Dict with optional keys:
                - file_category: Filter by category
                - folder_id: Filter by folder
                - starred_only: Only starred
                - owner: 'me', 'others', or specific user_id
                - date_from: Modified after
                - date_to: Modified before
        """
        filters = filters or {}
        
        domain = [
            ('owner_id', '=', self.env.user.id),
            ('is_trashed', '=', False),
        ]
        
        # Text search
        if query:
            domain.append('|')
            domain.append(('name', 'ilike', query))
            domain.append(('tags', 'ilike', query))
        
        # Category filter
        if filters.get('file_category'):
            domain.append(('file_category', '=', filters['file_category']))
        
        # Folder filter
        if filters.get('folder_id'):
            domain.append(('folder_id', '=', filters['folder_id']))
        
        # Starred filter
        if filters.get('starred_only'):
            domain.append(('is_starred', '=', True))
        
        # Date filters
        if filters.get('date_from'):
            domain.append(('write_date', '>=', filters['date_from']))
        if filters.get('date_to'):
            domain.append(('write_date', '<=', filters['date_to']))
        
        docs = self.search(domain, order='write_date desc', limit=100)
        return self._format_documents(docs)


# =============================================================================
# DOCUMENT TAG
# =============================================================================

class OfficeDocumentTag(models.Model):
    _name = 'office.document.tag'
    _description = 'Document Tag'
    _order = 'name'

    name = fields.Char(
        string='Name',
        required=True,
        index=True,
    )
    color = fields.Integer(
        string='Color Index',
        default=0,
    )
    
    _sql_constraints = [
        ('unique_name', 'UNIQUE(name)', 'Tag name must be unique.'),
    ]


# =============================================================================
# SHARE WIZARD (Enhanced)
# =============================================================================

class OfficeDocumentShareWizard(models.TransientModel):
    _name = 'office.document.share.wizard'
    _description = 'Share Document Wizard'

    document_id = fields.Many2one(
        'office.document',
        string='Document',
    )
    folder_id = fields.Many2one(
        'office.folder',
        string='Folder',
    )
    
    # Individual sharing
    user_ids = fields.Many2many(
        'res.users',
        string='Share With',
        domain=[('share', '=', False)],
    )
    permission = fields.Selection([
        ('viewer', 'Viewer'),
        ('commenter', 'Commenter'),
        ('editor', 'Editor'),
    ], string='Permission', default='viewer')
    notify_users = fields.Boolean(
        string='Send Notification',
        default=True,
    )
    message = fields.Text(
        string='Message',
        help='Optional message to include in notification',
    )
    
    # Link sharing
    enable_link = fields.Boolean(
        string='Anyone with Link',
        default=False,
    )
    link_permission = fields.Selection([
        ('viewer', 'Can View'),
        ('commenter', 'Can Comment'),
        ('editor', 'Can Edit'),
    ], string='Link Permission', default='viewer')
    link_url = fields.Char(
        string='Share Link',
        compute='_compute_link_url',
    )
    
    # Current access (display)
    current_access_html = fields.Html(
        string='Who Has Access',
        compute='_compute_current_access',
    )

    @api.depends('document_id', 'folder_id')
    def _compute_current_access(self):
        for wizard in self:
            html_parts = ['<div class="o_share_access_list">']
            
            target_type = 'document' if wizard.document_id else 'folder'
            target_id = wizard.document_id.id if wizard.document_id else wizard.folder_id.id
            
            if target_id:
                access_list = self.env['office.document.access'].get_access_list(
                    target_type, target_id
                )
                
                for access in access_list:
                    badge_class = 'bg-primary' if access['is_owner'] else 'bg-secondary'
                    inherited_badge = '<span class="badge bg-info">Inherited</span>' if access.get('is_inherited') else ''
                    
                    html_parts.append(f'''
                        <div class="d-flex align-items-center mb-2 p-2 border rounded">
                            <img src="{access['user_avatar']}" class="rounded-circle me-2" width="32" height="32"/>
                            <div class="flex-grow-1">
                                <div class="fw-bold">{access['user_name']}</div>
                                <div class="text-muted small">{access['user_email']}</div>
                            </div>
                            <span class="badge {badge_class} text-capitalize">{access['permission']}</span>
                            {inherited_badge}
                        </div>
                    ''')
            
            html_parts.append('</div>')
            wizard.current_access_html = ''.join(html_parts)

    @api.depends('document_id', 'folder_id', 'enable_link')
    def _compute_link_url(self):
        for wizard in self:
            if wizard.enable_link:
                target_type = 'document' if wizard.document_id else 'folder'
                target_id = wizard.document_id.id if wizard.document_id else wizard.folder_id.id
                
                if target_id:
                    link = self.env['office.share.link'].get_link_for_target(
                        target_type, target_id
                    )
                    if link:
                        wizard.link_url = link.get_share_url()
                    else:
                        # Create new link
                        link = self.env['office.share.link'].create_link(
                            target_type, target_id, wizard.link_permission
                        )
                        wizard.link_url = link.get_share_url()
                else:
                    wizard.link_url = False
            else:
                wizard.link_url = False

    def action_share(self):
        """Apply sharing settings."""
        self.ensure_one()
        
        target_type = 'document' if self.document_id else 'folder'
        target_id = self.document_id.id if self.document_id else self.folder_id.id
        
        # Grant access to selected users (creates access records)
        for user in self.user_ids:
            self.env['office.document.access'].sudo().grant_access(
                target_type, target_id, user.id,
                self.permission, self.notify_users
            )
        
        # Also update legacy shared_user_ids field for security rule compatibility
        if self.document_id and self.user_ids:
            self.document_id.sudo().write({
                'shared_user_ids': [(4, user.id) for user in self.user_ids]
            })
        elif self.folder_id and self.user_ids:
            self.folder_id.sudo().write({
                'shared_user_ids': [(4, user.id) for user in self.user_ids]
            })
        
        # Update link sharing
        if self.enable_link:
            link = self.env['office.share.link'].get_link_for_target(
                target_type, target_id
            )
            if link:
                link.write({
                    'permission': self.link_permission,
                    'is_active': True,
                })
            else:
                self.env['office.share.link'].create_link(
                    target_type, target_id, self.link_permission
                )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Shared'),
                'message': _('Sharing settings updated.'),
                'type': 'success',
            }
        }


# =============================================================================
# MOVE WIZARD
# =============================================================================

class OfficeDocumentMoveWizard(models.TransientModel):
    _name = 'office.document.move.wizard'
    _description = 'Move Document Wizard'

    document_id = fields.Many2one(
        'office.document',
        string='Document',
    )
    document_ids = fields.Many2many(
        'office.document',
        string='Documents',
    )
    current_folder_id = fields.Many2one(
        'office.folder',
        string='Current Folder',
        readonly=True,
    )
    target_folder_id = fields.Many2one(
        'office.folder',
        string='Move To',
        domain=[('owner_id', '=', lambda self: self.env.user.id)],
    )

    def action_move(self):
        """Move documents to target folder."""
        self.ensure_one()
        
        docs = self.document_ids or self.document_id
        for doc in docs:
            doc.folder_id = self.target_folder_id
        
        folder_name = self.target_folder_id.name if self.target_folder_id else 'My Drive'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Moved'),
                'message': _('%d item(s) moved to %s') % (len(docs), folder_name),
                'type': 'success',
            }
        }
