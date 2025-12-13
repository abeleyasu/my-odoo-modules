# -*- coding: utf-8 -*-
import base64
import logging
import os
import uuid
import mimetypes
from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.modules.module import get_module_resource

_logger = logging.getLogger(__name__)

# Document types supported by OnlyOffice
DOCUMENT_TYPES = [
    ('word', 'Word Document'),
    ('excel', 'Excel Spreadsheet'),
    ('powerpoint', 'PowerPoint Presentation'),
    ('pdf', 'PDF Document'),
    ('text', 'Text Document'),
]

# Template mapping for creating new documents from templates
TEMPLATE_MAP = {
    'word': ('blank.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.docx'),
    'excel': ('blank.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', '.xlsx'),
    'powerpoint': ('blank.pptx', 'application/vnd.openxmlformats-officedocument.presentationml.presentation', '.pptx'),
    'text': ('blank.txt', 'text/plain', '.txt'),
}

# Icon mapping for document types
DOCUMENT_ICONS = {
    'word': 'fa-file-word-o',
    'excel': 'fa-file-excel-o',
    'powerpoint': 'fa-file-powerpoint-o',
    'pdf': 'fa-file-pdf-o',
    'text': 'fa-file-text-o',
}

# Color mapping for document types
DOCUMENT_COLORS = {
    'word': '#2B5797',
    'excel': '#217346',
    'powerpoint': '#D24726',
    'pdf': '#E74C3C',
    'text': '#7F8C8D',
}

# Comprehensive mimetype mapping for uploads (supports all OnlyOffice formats)
MIMETYPE_TO_DOCTYPE = {
    # Word formats
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'word',
    'application/msword': 'word',
    'application/vnd.oasis.opendocument.text': 'word',
    'application/vnd.oasis.opendocument.text-template': 'word',
    'application/vnd.ms-word.document.macroenabled.12': 'word',
    'application/vnd.ms-word.template.macroenabled.12': 'word',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.template': 'word',
    'text/rtf': 'word',
    'application/rtf': 'word',
    'application/epub+zip': 'word',
    'text/html': 'word',
    # Excel formats
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'excel',
    'application/vnd.ms-excel': 'excel',
    'application/vnd.oasis.opendocument.spreadsheet': 'excel',
    'application/vnd.oasis.opendocument.spreadsheet-template': 'excel',
    'application/vnd.ms-excel.sheet.macroenabled.12': 'excel',
    'application/vnd.ms-excel.sheet.binary.macroenabled.12': 'excel',
    'application/vnd.ms-excel.template.macroenabled.12': 'excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.template': 'excel',
    'text/csv': 'excel',
    'application/csv': 'excel',
    # PowerPoint formats
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'powerpoint',
    'application/vnd.ms-powerpoint': 'powerpoint',
    'application/vnd.oasis.opendocument.presentation': 'powerpoint',
    'application/vnd.oasis.opendocument.presentation-template': 'powerpoint',
    'application/vnd.ms-powerpoint.presentation.macroenabled.12': 'powerpoint',
    'application/vnd.ms-powerpoint.slideshow.macroenabled.12': 'powerpoint',
    'application/vnd.ms-powerpoint.template.macroenabled.12': 'powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.template': 'powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.slideshow': 'powerpoint',
    # PDF formats
    'application/pdf': 'pdf',
    'application/acrobat': 'pdf',
    'application/x-pdf': 'pdf',
    'image/pdf': 'pdf',
    # Text formats
    'text/plain': 'text',
    'text/markdown': 'text',
}


class OfficeDocument(models.Model):
    _name = 'office.document'
    _description = 'Office Document'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'write_date desc'

    name = fields.Char(
        string='Document Name',
        required=True,
        tracking=True,
        index=True,
    )
    document_type = fields.Selection(
        selection=DOCUMENT_TYPES,
        string='Document Type',
        required=True,
        default='word',
        tracking=True,
        index=True,
    )
    attachment_id = fields.Many2one(
        'ir.attachment',
        string='Attachment',
        required=True,
        ondelete='cascade',
    )
    file_size = fields.Integer(
        string='File Size (bytes)',
        compute='_compute_file_size',
        store=True,
    )
    file_size_human = fields.Char(
        string='File Size',
        compute='_compute_file_size_human',
    )
    owner_id = fields.Many2one(
        'res.users',
        string='Owner',
        default=lambda self: self.env.user,
        required=True,
        tracking=True,
        index=True,
    )
    shared_user_ids = fields.Many2many(
        'res.users',
        'office_document_share_rel',
        'document_id',
        'user_id',
        string='Shared With',
    )
    folder_id = fields.Many2one(
        'office.folder',
        string='Folder',
        ondelete='set null',
        index=True,
    )
    is_template = fields.Boolean(
        string='Is Template',
        default=False,
    )
    original_document_id = fields.Many2one(
        'office.document',
        string='Original Document',
        help='Reference to original document if this is a copy',
        ondelete='set null',
    )
    icon = fields.Char(
        string='Icon',
        compute='_compute_icon',
    )
    color = fields.Char(
        string='Color',
        compute='_compute_color',
    )
    
    # Google Drive-like features
    is_starred = fields.Boolean(
        string='Starred',
        default=False,
        index=True,
    )
    is_trashed = fields.Boolean(
        string='In Trash',
        default=False,
        index=True,
    )
    trashed_date = fields.Datetime(
        string='Trashed Date',
    )
    last_accessed = fields.Datetime(
        string='Last Accessed',
        default=fields.Datetime.now,
    )
    access_count = fields.Integer(
        string='Access Count',
        default=0,
    )
    share_link = fields.Char(
        string='Share Link',
        copy=False,
    )
    share_link_active = fields.Boolean(
        string='Share Link Active',
        default=False,
    )
    share_permission = fields.Selection([
        ('view', 'Can View'),
        ('edit', 'Can Edit'),
    ], string='Share Permission', default='view')
    description = fields.Text(
        string='Description',
    )
    tags = fields.Char(
        string='Tags',
        help='Comma-separated tags for better search',
    )
    
    @api.depends('attachment_id.file_size')
    def _compute_file_size(self):
        for record in self:
            record.file_size = record.attachment_id.file_size if record.attachment_id else 0

    @api.depends('file_size')
    def _compute_file_size_human(self):
        for record in self:
            size = record.file_size
            if size < 1024:
                record.file_size_human = f'{size} B'
            elif size < 1024 * 1024:
                record.file_size_human = f'{size / 1024:.1f} KB'
            elif size < 1024 * 1024 * 1024:
                record.file_size_human = f'{size / (1024 * 1024):.1f} MB'
            else:
                record.file_size_human = f'{size / (1024 * 1024 * 1024):.1f} GB'

    @api.depends('document_type')
    def _compute_icon(self):
        for record in self:
            record.icon = DOCUMENT_ICONS.get(record.document_type, 'fa-file-o')

    @api.depends('document_type')
    def _compute_color(self):
        for record in self:
            record.color = DOCUMENT_COLORS.get(record.document_type, '#875A7B')

    @api.constrains('name')
    def _check_name(self):
        for record in self:
            if not record.name or not record.name.strip():
                raise ValidationError(_('Document name cannot be empty.'))

    @api.model
    def create_document_from_template(self, doc_type, folder_id=False):
        """Create a new document from template (called via ORM).

        Args:
            doc_type (str): one of DOCUMENT_TYPES keys
            folder_id (int|False): optional folder destination
        """
        # Handle dict/list parameters from XML-RPC
        if folder_id:
            if isinstance(folder_id, dict):
                folder_id = folder_id.get('id', False)
            elif isinstance(folder_id, (list, tuple)):
                folder_id = folder_id[0] if folder_id else False
            try:
                folder_id = int(folder_id) if folder_id else False
            except (ValueError, TypeError):
                folder_id = False
        else:
            folder_id = False
            
        if doc_type not in TEMPLATE_MAP:
            raise UserError(_('Invalid document type'))
        
        template_file, mimetype, file_ext = TEMPLATE_MAP[doc_type]
        
        # Get template file path using Odoo helper
        template_path = get_module_resource('office_document_creator', 'static', 'templates', template_file)
        
        if not template_path or not os.path.exists(template_path):
            raise UserError(_('Template file not found: %s') % template_file)
        
        # Read template file
        with open(template_path, 'rb') as f:
            file_data = f.read()
        
        # Generate unique name
        doc_names = {
            'word': 'Untitled Document',
            'excel': 'Untitled Spreadsheet',
            'powerpoint': 'Untitled Presentation',
        }
        base_name = doc_names.get(doc_type, 'Untitled')
        count = 1
        name = base_name
        
        while self.search([('name', '=', name), ('owner_id', '=', self.env.user.id), ('is_trashed', '=', False)], limit=1):
            name = f'{base_name} {count}'
            count += 1
        
        # Create attachment with public access for ONLYOFFICE
        attachment_name = f"{name}{file_ext}"
        attachment = self.env['ir.attachment'].create({
            'name': attachment_name,
            'datas': base64.b64encode(file_data),
            'mimetype': mimetype,
            'res_model': 'office.document',
            'public': True,
        })
        
        # Create document
        document = self.create({
            'name': name,
            'document_type': doc_type,
            'attachment_id': attachment.id,
            'owner_id': self.env.user.id,
            'folder_id': folder_id or False,
        })
        
        # Link attachment to document
        attachment.res_id = document.id
        
        return {
            'document_id': document.id,
            'name': name,
            'attachment_id': attachment.id,
        }

    def action_open_editor(self):
        """Open document in ONLYOFFICE editor.
        
        Opens in a new tab to prevent redirect issues with PowerPoint presentations
        when navigating between slides. The OnlyOffice editor's goback feature
        can cause unwanted redirects when opened in the current tab.
        """
        self.ensure_one()
        if not self.attachment_id:
            raise UserError(_('No file attached to this document.'))
        
        # Update access tracking
        self.sudo().write({
            'last_accessed': fields.Datetime.now(),
            'access_count': self.access_count + 1,
        })
        
        url = f'/onlyoffice/editor/{self.attachment_id.id}'
        
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',  # Open in new tab to prevent redirect issues
        }

    def action_duplicate(self):
        """Create a copy of the document"""
        self.ensure_one()
        
        original_data = base64.b64decode(self.attachment_id.datas)
        _template_file, _mimetype, file_ext = TEMPLATE_MAP.get(self.document_type, ('', '', '.docx'))
        
        copy_number = 1
        base_name = self.name
        if '(Copy' in self.name:
            base_name = self.name.split('(Copy')[0].strip()
        
        new_name = f'{base_name} (Copy {copy_number})'
        while self.search([('name', '=', new_name), ('owner_id', '=', self.owner_id.id), ('is_trashed', '=', False)], limit=1):
            copy_number += 1
            new_name = f'{base_name} (Copy {copy_number})'
        
        attachment_name = f"{new_name}{file_ext}"
        new_attachment = self.env['ir.attachment'].create({
            'name': attachment_name,
            'datas': base64.b64encode(original_data),
            'mimetype': self.attachment_id.mimetype,
            'res_model': 'office.document',
            'public': True,
        })
        
        new_document = self.create({
            'name': new_name,
            'document_type': self.document_type,
            'attachment_id': new_attachment.id,
            'owner_id': self.env.user.id,
            'folder_id': self.folder_id.id if self.folder_id else False,
            'original_document_id': self.id,
        })
        
        new_attachment.res_id = new_document.id
        
        _logger.info(f'Document duplicated: {self.name} -> {new_name}')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Document duplicated successfully!'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_rename(self, new_name):
        """Rename the document and its underlying attachment (preserve extension).

        Called from the JS UI. Performs a uniqueness check per owner and updates
        the `ir.attachment` name accordingly.
        """
        self.ensure_one()
        new_name = (new_name or '').strip()
        if not new_name:
            raise ValidationError(_('Document name cannot be empty.'))

        # Check for existing document with same name for the owner (not trashed)
        existing = self.search([
            ('id', '!=', self.id),
            ('name', '=', new_name),
            ('owner_id', '=', self.owner_id.id),
            ('is_trashed', '=', False),
        ], limit=1)
        if existing:
            raise ValidationError(_('A document with this name already exists.'))

        # Update attachment name preserving extension
        if self.attachment_id:
            old_att_name = self.attachment_id.name or ''
            base, ext = os.path.splitext(old_att_name)
            if not ext:
                # Fallback based on document type
                ext = TEMPLATE_MAP.get(self.document_type, ('', '', '.docx'))[2]

            attachment_name = f"{new_name}{ext}"
            # write via sudo to avoid access issues updating attachments
            self.attachment_id.sudo().write({'name': attachment_name})

        # Update document name
        self.write({'name': new_name})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Renamed'),
                'message': _('Document renamed successfully.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_toggle_star(self):
        """Toggle starred status"""
        self.ensure_one()
        self.is_starred = not self.is_starred
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Starred') if self.is_starred else _('Unstarred'),
                'message': _('Document added to starred') if self.is_starred else _('Document removed from starred'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_move_to_trash(self):
        """Move document to trash"""
        self.ensure_one()
        self.write({
            'is_trashed': True,
            'trashed_date': fields.Datetime.now(),
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Moved to Trash'),
                'message': _('Document moved to trash. It will be permanently deleted after 30 days.'),
                'type': 'warning',
                'sticky': False,
            }
        }

    def action_restore_from_trash(self):
        """Restore document from trash"""
        self.ensure_one()
        self.write({
            'is_trashed': False,
            'trashed_date': False,
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Restored'),
                'message': _('Document restored from trash.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_permanent_delete(self):
        """Permanently delete document"""
        self.ensure_one()
        self.unlink()
        return {
            'type': 'ir.actions.act_window_close',
        }

    def _compute_share_url(self):
        self.ensure_one()
        if not self.share_link or not self.share_link_active:
            return False
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base_url}/office/share/{self.share_link}"

    def action_generate_share_link(self):
        """Generate a public share link"""
        self.ensure_one()
        if not self.share_link:
            self.share_link = str(uuid.uuid4())
        self.share_link_active = True
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Share Link Generated'),
                'message': _('Share link has been created and activated.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_disable_share_link(self):
        """Disable public share link"""
        self.ensure_one()
        self.share_link_active = False
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Share Link Disabled'),
                'message': _('Share link has been disabled.'),
                'type': 'info',
                'sticky': False,
            }
        }

    def action_share(self):
        """Open wizard to share document"""
        self.ensure_one()
        # Return a fully-formed window action including `views` to satisfy the web client
        return {
            'name': _('Share Document'),
            'type': 'ir.actions.act_window',
            'res_model': 'office.document.share.wizard',
            'view_mode': 'form',
            'views': [[False, 'form']],
            'target': 'new',
            'context': {'default_document_id': self.id},
        }

    def get_share_link_info(self):
        """Return link-sharing metadata for dashboards/modals."""
        self.ensure_one()
        if self.owner_id != self.env.user:
            raise UserError(_('Only the owner can manage the public link.'))
        url = self._compute_share_url()
        return {
            'active': bool(self.share_link_active),
            'permission': self.share_permission,
            'token': self.share_link,
            'url': url or False,
        }

    def update_share_link(self, permission='view', active=True, regenerate=False):
        """Update share link settings, optionally regenerate token."""
        self.ensure_one()
        if self.owner_id != self.env.user:
            raise UserError(_('Only the owner can manage the public link.'))
        vals = {
            'share_permission': permission,
            'share_link_active': active,
        }
        if regenerate or (active and not self.share_link):
            vals['share_link'] = str(uuid.uuid4())
        self.write(vals)
        return self.get_share_link_info()

    def action_download(self):
        """Download the document"""
        self.ensure_one()
        if not self.attachment_id:
            raise UserError(_('No file attached to this document.'))
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.attachment_id.id}?download=true',
            'target': 'self',
        }

    def action_move_to_folder(self):
        """Open wizard to move document to folder"""
        self.ensure_one()
        return {
            'name': _('Move to Folder'),
            'type': 'ir.actions.act_window',
            'res_model': 'office.document.move.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_document_id': self.id, 'default_current_folder_id': self.folder_id.id if self.folder_id else False},
        }

    # ---- Lightweight RPC helpers for SPA/dashboard flows ----
    @api.model
    def move_document(self, document_id, target_folder_id=False):
        """Move a document to a target folder (or root)."""
        # Handle dict/list parameters from XML-RPC
        if isinstance(document_id, dict):
            document_id = document_id.get('id')
        elif isinstance(document_id, (list, tuple)):
            document_id = document_id[0] if document_id else False
        
        if target_folder_id:
            if isinstance(target_folder_id, dict):
                target_folder_id = target_folder_id.get('id', False)
            elif isinstance(target_folder_id, (list, tuple)):
                target_folder_id = target_folder_id[0] if target_folder_id else False
            try:
                target_folder_id = int(target_folder_id) if target_folder_id else False
            except (ValueError, TypeError):
                target_folder_id = False
        else:
            target_folder_id = False
            
        doc = self.browse(document_id).exists()
        if not doc:
            raise UserError(_('Document not found'))
        if doc.owner_id != self.env.user:
            raise UserError(_('You can only move your own documents.'))
        doc.write({'folder_id': target_folder_id or False})
        return True

    @api.model
    def upload_document(self, filename, file_data, folder_id=False):
        """Upload an existing document file"""
        # Decode base64 data
        if isinstance(file_data, str):
            file_data = base64.b64decode(file_data)
        
        # Determine document type from mimetype
        mimetype, _encoding = mimetypes.guess_type(filename)
        doc_type = MIMETYPE_TO_DOCTYPE.get(mimetype, 'word')
        
        # Get file extension
        _base_name_temp, file_ext = os.path.splitext(filename)
        if not file_ext:
            file_ext = TEMPLATE_MAP.get(doc_type, ('', '', '.docx'))[2]
        
        # Generate unique name
        base_name = os.path.splitext(filename)[0]
        name = base_name
        count = 1
        
        while self.search([('name', '=', name), ('owner_id', '=', self.env.user.id), ('is_trashed', '=', False)], limit=1):
            name = f'{base_name} ({count})'
            count += 1
        
        # Create attachment
        attachment_name = f"{name}{file_ext}"
        attachment = self.env['ir.attachment'].create({
            'name': attachment_name,
            'datas': base64.b64encode(file_data) if isinstance(file_data, bytes) else file_data,
            'mimetype': mimetype or 'application/octet-stream',
            'res_model': 'office.document',
            'public': True,
        })
        
        # Create document
        document = self.create({
            'name': name,
            'document_type': doc_type,
            'attachment_id': attachment.id,
            'owner_id': self.env.user.id,
            'folder_id': folder_id if folder_id else False,
        })
        
        # Link attachment to document
        attachment.res_id = document.id
        
        return {
            'document_id': document.id,
            'name': name,
        }

    @api.model
    def get_recent_documents(self, limit=10):
        """Get recently accessed documents"""
        docs = self.search([
            ('owner_id', '=', self.env.user.id),
            ('is_trashed', '=', False),
        ], order='last_accessed desc', limit=limit)
        return docs.read(['id', 'name', 'document_type', 'icon', 'color', 'write_date', 'file_size_human', 'is_starred'])

    @api.model
    def get_starred_documents(self):
        """Get starred documents"""
        docs = self.search([
            ('owner_id', '=', self.env.user.id),
            ('is_starred', '=', True),
            ('is_trashed', '=', False),
        ], order='name')
        return docs.read(['id', 'name', 'document_type', 'icon', 'color', 'write_date', 'file_size_human', 'is_starred'])

    @api.model
    def get_shared_with_me(self):
        """Get documents shared with current user"""
        docs = self.search([
            ('shared_user_ids', 'in', [self.env.user.id]),
            ('is_trashed', '=', False),
        ], order='write_date desc')
        return docs.read(['id', 'name', 'document_type', 'icon', 'color', 'write_date', 'file_size_human', 'is_starred', 'owner_id'])

    @api.model
    def get_trash_documents(self):
        """Get documents in trash"""
        docs = self.search([
            ('owner_id', '=', self.env.user.id),
            ('is_trashed', '=', True),
        ], order='trashed_date desc')
        return docs.read(['id', 'name', 'document_type', 'icon', 'color', 'trashed_date', 'file_size_human', 'is_starred'])

    @api.model
    def get_documents_in_folder(self, folder_id=False):
        """List documents inside a folder (root when folder_id is False)."""
        # Handle dict/list parameters from XML-RPC
        if folder_id:
            if isinstance(folder_id, dict):
                folder_id = folder_id.get('id', False)
            elif isinstance(folder_id, (list, tuple)):
                folder_id = folder_id[0] if folder_id else False
            try:
                folder_id = int(folder_id) if folder_id else False
            except (ValueError, TypeError):
                folder_id = False
        else:
            folder_id = False
            
        domain = [
            ('owner_id', '=', self.env.user.id),
            ('is_trashed', '=', False),
        ]
        if folder_id:
            domain.append(('folder_id', '=', folder_id))
        else:
            domain.append(('folder_id', '=', False))

        docs = self.search(domain, order='write_date desc')
        return docs.read(['id', 'name', 'document_type', 'icon', 'color', 'write_date', 'file_size_human', 'is_starred', 'folder_id'])

    @api.model
    def empty_trash(self):
        """Permanently delete all trashed documents"""
        trashed = self.search([
            ('owner_id', '=', self.env.user.id),
            ('is_trashed', '=', True),
        ])
        count = len(trashed)
        trashed.unlink()
        return count

    @api.model
    def get_storage_stats(self):
        """Get storage statistics for current user"""
        docs = self.search([('owner_id', '=', self.env.user.id), ('is_trashed', '=', False)])
        total_size = sum(docs.mapped('file_size'))
        doc_count = len(docs)
        
        # Count by type (include all supported types)
        by_type = {
            'word': 0,
            'excel': 0,
            'powerpoint': 0,
            'pdf': 0,
            'text': 0,
        }
        for doc in docs:
            by_type[doc.document_type] = by_type.get(doc.document_type, 0) + 1
        
        return {
            'total_size': total_size,
            'total_size_human': self._format_size(total_size),
            'document_count': doc_count,
            'by_type': by_type,
        }

    def _format_size(self, size):
        """Format size in human readable format"""
        if size < 1024:
            return f'{size} B'
        elif size < 1024 * 1024:
            return f'{size / 1024:.1f} KB'
        elif size < 1024 * 1024 * 1024:
            return f'{size / (1024 * 1024):.1f} MB'
        else:
            return f'{size / (1024 * 1024 * 1024):.1f} GB'

    @api.model
    def search_documents(self, query, doc_type=False, folder_id=False, starred_only=False):
        """Search documents with various filters"""
        domain = [
            ('owner_id', '=', self.env.user.id),
            ('is_trashed', '=', False),
        ]
        
        if query:
            domain.append('|')
            domain.append(('name', 'ilike', query))
            domain.append(('tags', 'ilike', query))
        
        if doc_type:
            domain.append(('document_type', '=', doc_type))
        
        if folder_id:
            domain.append(('folder_id', '=', folder_id))
        
        if starred_only:
            domain.append(('is_starred', '=', True))
        
        docs = self.search(domain, order='write_date desc')
        return docs.read(['id', 'name', 'document_type', 'icon', 'color', 'write_date', 'file_size_human', 'is_starred', 'folder_id'])

    def unlink(self):
        """Override unlink to also delete attachments"""
        attachments = self.mapped('attachment_id')
        res = super().unlink()
        attachments.unlink()
        return res

    @api.model
    def auto_delete_old_trash(self):
        """Cron job to auto-delete documents in trash for more than 30 days"""
        cutoff_date = fields.Datetime.now() - timedelta(days=30)
        old_trash = self.search([
            ('is_trashed', '=', True),
            ('trashed_date', '<', cutoff_date),
        ])
        count = len(old_trash)
        old_trash.unlink()
        _logger.info(f'Auto-deleted {count} documents from trash (older than 30 days)')
        return count


class OfficeDocumentShareWizard(models.TransientModel):
    _name = 'office.document.share.wizard'
    _description = 'Share Document Wizard'

    document_id = fields.Many2one('office.document', string='Document', required=True)
    user_ids = fields.Many2many('res.users', string='Share With Users')
    share_link_active = fields.Boolean(string='Enable Share Link', related='document_id.share_link_active', readonly=False)
    share_permission = fields.Selection([
        ('view', 'Can View'),
        ('edit', 'Can Edit'),
    ], string='Permission', default='view')
    share_link = fields.Char(string='Share Link', related='document_id.share_link', readonly=True)

    def action_share(self):
        """Share the document with selected users"""
        self.ensure_one()
        if self.user_ids:
            self.document_id.shared_user_ids = [(4, user.id) for user in self.user_ids]
        
        if self.share_link_active and not self.document_id.share_link:
            self.document_id.share_link = str(uuid.uuid4())
        
        self.document_id.share_permission = self.share_permission
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Shared'),
                'message': _('Document sharing settings updated.'),
                'type': 'success',
                'sticky': False,
            }
        }


class OfficeDocumentMoveWizard(models.TransientModel):
    _name = 'office.document.move.wizard'
    _description = 'Move Document Wizard'

    document_id = fields.Many2one('office.document', string='Document', required=True)
    current_folder_id = fields.Many2one('office.folder', string='Current Folder', readonly=True)
    target_folder_id = fields.Many2one('office.folder', string='Move To')

    def action_move(self):
        """Move the document to selected folder"""
        self.ensure_one()
        self.document_id.folder_id = self.target_folder_id
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Moved'),
                'message': _('Document moved to %s.') % (self.target_folder_id.name if self.target_folder_id else 'My Drive'),
                'type': 'success',
                'sticky': False,
            }
        }
