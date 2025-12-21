# -*- coding: utf-8 -*-
# Copyright 2025 Odoo Community
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""
Office Document Controllers - Enterprise Document Management System

Controllers for:
- Public share links
- File previews (images, videos, audio, code, PDF)
- Chunked file upload for large files (up to 10GB)
- Folder operations
- Download with access control
"""

import base64
import hashlib
import io
import json
import logging
import mimetypes
import os
import tempfile
import uuid
from datetime import datetime, timedelta

from odoo import http, _
from odoo.http import request, Response
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)

# Chunked upload configuration
CHUNK_SIZE = 5 * 1024 * 1024  # 5MB chunks
MAX_FILE_SIZE = 10 * 1024 * 1024 * 1024  # 10GB
UPLOAD_TEMP_DIR = '/tmp/odoo_office_uploads'

# Ensure temp directory exists
os.makedirs(UPLOAD_TEMP_DIR, exist_ok=True)


class OfficeController(http.Controller):
    """Main controller for office document management."""

    # =========================================================================
    # PUBLIC SHARE LINKS
    # =========================================================================

    @http.route('/office/share/<string:token>', type='http', auth='public', website=True)
    def public_share(self, token, password=None, **kwargs):
        """Access a shared document or folder via public link.
        
        This is the main endpoint for Google Drive-like sharing.
        """
        # Find share link
        ShareLink = request.env['office.share.link'].sudo()
        link = ShareLink.search([('token', '=', token)], limit=1)
        
        if not link:
            return request.render('office_document_creator.share_not_found', {
                'message': _('This link does not exist or has been removed.')
            })
        
        # Validate access
        is_valid, error = link.validate_access(password)
        
        if not is_valid:
            if link.requires_password and not password:
                # Show password form
                return request.render('office_document_creator.share_password_required', {
                    'token': token,
                })
            return request.render('office_document_creator.share_error', {
                'message': error
            })
        
        # Track view
        link.track_view()
        
        # Route to appropriate view
        if link.document_id:
            return self._render_shared_document(link)
        elif link.folder_id:
            return self._render_shared_folder(link)
        else:
            return request.render('office_document_creator.share_error', {
                'message': _('Invalid share link.')
            })

    def _render_shared_document(self, link):
        """Render shared document view with OnlyOffice support."""
        doc = link.document_id
        
        # Check if document can be edited in OnlyOffice
        office_file_types = ['word', 'excel', 'powerpoint', 'text']
        can_use_onlyoffice = doc.file_category in office_file_types and doc.attachment_id
        
        # If permission allows editing/viewing and file type supports it, use OnlyOffice
        if can_use_onlyoffice and link.permission in ('editor', 'commenter', 'viewer'):
            # Determine OnlyOffice mode
            if link.permission == 'editor':
                mode = 'edit'
            elif link.permission == 'commenter':
                mode = 'comment'  # OnlyOffice supports comment-only mode
            else:
                mode = 'view'
            
            # Build OnlyOffice URL with share token for authentication
            onlyoffice_url = f'/onlyoffice/editor/{doc.attachment_id.id}?share_token={link.token}&mode={mode}'
            
            # Redirect to OnlyOffice editor
            return request.redirect(onlyoffice_url)
        
        # For other file types or download-only, render preview page
        return request.render('office_document_creator.shared_document_view', {
            'document': doc,
            'link': link,
            'can_download': link.allow_download,
            'can_edit': link.permission == 'editor',
            'can_view_online': can_use_onlyoffice,
            'preview_url': f'/office/preview/{doc.id}?token={link.token}',
            'download_url': f'/office/download/{doc.id}?token={link.token}' if link.allow_download else None,
            'onlyoffice_url': f'/onlyoffice/editor/{doc.attachment_id.id}?share_token={link.token}&mode=view' if can_use_onlyoffice else None,
        })

    def _render_shared_folder(self, link):
        """Render shared folder view."""
        folder = link.folder_id
        
        # Get folder contents
        documents = folder.document_ids.filtered(lambda d: not d.is_trashed)
        subfolders = folder.child_ids.filtered(lambda f: not f.is_trashed)
        
        return request.render('office_document_creator.shared_folder_view', {
            'folder': folder,
            'link': link,
            'documents': documents,
            'subfolders': subfolders,
            'can_download': link.allow_download,
        })

    @http.route('/office/share/<string:token>/password', type='http', auth='public', methods=['POST'], csrf=False)
    def share_password_submit(self, token, password=None, **kwargs):
        """Submit password for protected share link."""
        ShareLink = request.env['office.share.link'].sudo()
        link = ShareLink.search([('token', '=', token)], limit=1)
        
        if not link:
            return request.redirect('/office/share/' + token)
        
        is_valid, error = link.validate_access(password)
        
        if is_valid:
            # Set session cookie for password
            response = request.redirect(f'/office/share/{token}')
            response.set_cookie(f'share_pass_{token}', password, httponly=True, max_age=3600)
            return response
        
        return request.render('office_document_creator.share_password_required', {
            'token': token,
            'error': error,
        })

    # =========================================================================
    # FILE PREVIEW ENDPOINTS
    # =========================================================================

    @http.route('/office/preview/<int:document_id>', type='http', auth='public')
    def preview_document(self, document_id, token=None, **kwargs):
        """Main preview endpoint - routes to appropriate viewer."""
        doc = self._get_document_with_access(document_id, token)
        if not doc:
            return request.not_found()
        
        preview_type = doc.preview_type
        
        if preview_type == 'image':
            return self._preview_image(doc, token)
        elif preview_type == 'video':
            return self._preview_video(doc, token)
        elif preview_type == 'audio':
            return self._preview_audio(doc, token)
        elif preview_type == 'pdf':
            return self._preview_pdf(doc, token)
        elif preview_type == 'code':
            return self._preview_code(doc, token)
        elif preview_type == 'text':
            return self._preview_text(doc, token)
        elif preview_type == 'office':
            return request.redirect(f'/onlyoffice/editor/{doc.attachment_id.id}')
        else:
            # No preview available - offer download
            return request.render('office_document_creator.preview_not_available', {
                'document': doc,
                'download_url': f'/office/download/{doc.id}',
            })

    def _preview_image(self, doc, token=None):
        """Render image viewer."""
        return request.render('office_document_creator.preview_image', {
            'document': doc,
            'image_url': f'/web/content/{doc.attachment_id.id}',
            'download_url': f'/office/download/{doc.id}',
            'token': token,
        })

    def _preview_video(self, doc, token=None):
        """Render video player."""
        return request.render('office_document_creator.preview_video', {
            'document': doc,
            'video_url': f'/web/content/{doc.attachment_id.id}',
            'mimetype': doc.mimetype,
            'download_url': f'/office/download/{doc.id}',
            'token': token,
        })

    def _preview_audio(self, doc, token=None):
        """Render audio player."""
        return request.render('office_document_creator.preview_audio', {
            'document': doc,
            'audio_url': f'/web/content/{doc.attachment_id.id}',
            'mimetype': doc.mimetype,
            'download_url': f'/office/download/{doc.id}',
            'token': token,
        })

    def _preview_pdf(self, doc, token=None):
        """Render PDF viewer using PDF.js."""
        return request.render('office_document_creator.preview_pdf', {
            'document': doc,
            'pdf_url': f'/web/content/{doc.attachment_id.id}',
            'download_url': f'/office/download/{doc.id}',
            'token': token,
        })

    def _preview_code(self, doc, token=None):
        """Render code viewer using Monaco Editor."""
        # Read file content
        try:
            content = base64.b64decode(doc.attachment_id.datas).decode('utf-8', errors='replace')
        except Exception:
            content = '// Unable to decode file content'
        
        return request.render('office_document_creator.preview_code', {
            'document': doc,
            'content': content,
            'language': doc.code_language or 'plaintext',
            'download_url': f'/office/download/{doc.id}',
            'token': token,
        })

    def _preview_text(self, doc, token=None):
        """Render plain text viewer."""
        try:
            content = base64.b64decode(doc.attachment_id.datas).decode('utf-8', errors='replace')
        except Exception:
            content = 'Unable to decode file content'
        
        return request.render('office_document_creator.preview_text', {
            'document': doc,
            'content': content,
            'download_url': f'/office/download/{doc.id}',
            'token': token,
        })

    def _get_document_with_access(self, document_id, token=None):
        """Get document if user has access (or valid share token)."""
        Document = request.env['office.document']
        
        # Try with token first (public access)
        if token:
            ShareLink = request.env['office.share.link'].sudo()
            link = ShareLink.search([
                ('token', '=', token),
                ('document_id', '=', document_id),
                ('is_active', '=', True),
            ], limit=1)
            
            if link:
                is_valid, _ = link.validate_access()
                if is_valid:
                    return link.document_id.sudo()
        
        # Try with user authentication
        if request.env.user and request.env.user.id:
            try:
                doc = Document.browse(document_id)
                if doc.exists():
                    # Check access
                    doc.check_access_rights('read')
                    doc.check_access_rule('read')
                    return doc
            except AccessError:
                pass
        
        return None

    # =========================================================================
    # DOWNLOAD
    # =========================================================================

    @http.route('/office/download/<int:document_id>', type='http', auth='public')
    def download_document(self, document_id, token=None, **kwargs):
        """Download document with access control."""
        doc = self._get_document_with_access(document_id, token)
        if not doc:
            return request.not_found()
        
        # Check download permission for share links
        if token:
            ShareLink = request.env['office.share.link'].sudo()
            link = ShareLink.search([
                ('token', '=', token),
                ('document_id', '=', document_id),
            ], limit=1)
            
            if link and not link.allow_download:
                return request.render('office_document_creator.download_not_allowed')
        
        # Log download activity
        if request.env.user and request.env.user.id:
            request.env['office.document.activity'].sudo().log_activity(
                'document', document_id, 'download'
            )
        
        # Return file
        return request.redirect(f'/web/content/{doc.attachment_id.id}?download=true')

    # =========================================================================
    # CHUNKED UPLOAD (for large files up to 10GB)
    # =========================================================================

    @http.route('/office/upload/init', type='json', auth='user')
    def upload_init(self, filename, file_size, folder_id=False, **kwargs):
        """Initialize a chunked upload session.
        
        Args:
            filename: Original filename
            file_size: Total file size in bytes
            folder_id: Optional target folder
            
        Returns:
            upload_id: Unique upload session ID
            chunk_size: Recommended chunk size
        """
        # Validate file size
        if file_size > MAX_FILE_SIZE:
            raise UserError(_(
                'File size exceeds maximum limit of 10 GB.'
            ))
        
        # Generate upload session ID
        upload_id = str(uuid.uuid4())
        
        # Store upload metadata
        upload_dir = os.path.join(UPLOAD_TEMP_DIR, upload_id)
        os.makedirs(upload_dir, exist_ok=True)
        
        metadata = {
            'filename': filename,
            'file_size': file_size,
            'folder_id': folder_id,
            'user_id': request.env.user.id,
            'created_at': datetime.now().isoformat(),
            'chunks_received': [],
            'total_chunks': (file_size + CHUNK_SIZE - 1) // CHUNK_SIZE,
        }
        
        with open(os.path.join(upload_dir, 'metadata.json'), 'w') as f:
            json.dump(metadata, f)
        
        _logger.info(f'Initialized upload {upload_id} for {filename} ({file_size} bytes)')
        
        return {
            'upload_id': upload_id,
            'chunk_size': CHUNK_SIZE,
            'total_chunks': metadata['total_chunks'],
        }

    @http.route('/office/upload/chunk', type='http', auth='user', methods=['POST'], csrf=False)
    def upload_chunk(self, upload_id, chunk_index, chunk_data, **kwargs):
        """Upload a single chunk.
        
        Args:
            upload_id: Upload session ID
            chunk_index: 0-based chunk index
            chunk_data: Base64 encoded chunk data
            
        Returns:
            JSON with success status and progress
        """
        upload_dir = os.path.join(UPLOAD_TEMP_DIR, upload_id)
        
        if not os.path.exists(upload_dir):
            return Response(
                json.dumps({'error': 'Upload session not found'}),
                content_type='application/json',
                status=404
            )
        
        # Read metadata
        with open(os.path.join(upload_dir, 'metadata.json'), 'r') as f:
            metadata = json.load(f)
        
        # Verify user
        if metadata['user_id'] != request.env.user.id:
            return Response(
                json.dumps({'error': 'Access denied'}),
                content_type='application/json',
                status=403
            )
        
        # Save chunk
        chunk_index = int(chunk_index)
        chunk_path = os.path.join(upload_dir, f'chunk_{chunk_index:06d}')
        
        # Handle file upload
        if hasattr(chunk_data, 'read'):
            chunk_bytes = chunk_data.read()
        else:
            chunk_bytes = base64.b64decode(chunk_data)
        
        with open(chunk_path, 'wb') as f:
            f.write(chunk_bytes)
        
        # Update metadata
        if chunk_index not in metadata['chunks_received']:
            metadata['chunks_received'].append(chunk_index)
        
        with open(os.path.join(upload_dir, 'metadata.json'), 'w') as f:
            json.dump(metadata, f)
        
        progress = len(metadata['chunks_received']) / metadata['total_chunks'] * 100
        
        return Response(
            json.dumps({
                'success': True,
                'chunk_index': chunk_index,
                'progress': progress,
                'chunks_received': len(metadata['chunks_received']),
                'total_chunks': metadata['total_chunks'],
            }),
            content_type='application/json'
        )

    @http.route('/office/upload/complete', type='json', auth='user')
    def upload_complete(self, upload_id, **kwargs):
        """Complete chunked upload - merge chunks and create document.
        
        Args:
            upload_id: Upload session ID
            
        Returns:
            Document info dict
        """
        upload_dir = os.path.join(UPLOAD_TEMP_DIR, upload_id)
        
        if not os.path.exists(upload_dir):
            raise UserError(_('Upload session not found'))
        
        # Read metadata
        with open(os.path.join(upload_dir, 'metadata.json'), 'r') as f:
            metadata = json.load(f)
        
        # Verify all chunks received
        if len(metadata['chunks_received']) != metadata['total_chunks']:
            raise UserError(_(
                'Upload incomplete: %d/%d chunks received'
            ) % (len(metadata['chunks_received']), metadata['total_chunks']))
        
        # Merge chunks
        _logger.info(f'Merging {metadata["total_chunks"]} chunks for {metadata["filename"]}')
        
        merged_data = io.BytesIO()
        for i in range(metadata['total_chunks']):
            chunk_path = os.path.join(upload_dir, f'chunk_{i:06d}')
            with open(chunk_path, 'rb') as f:
                merged_data.write(f.read())
        
        merged_data.seek(0)
        file_bytes = merged_data.read()
        
        # Create document
        result = request.env['office.document'].upload_document(
            metadata['filename'],
            file_bytes,
            metadata.get('folder_id', False)
        )
        
        # Cleanup temp files
        import shutil
        shutil.rmtree(upload_dir, ignore_errors=True)
        
        _logger.info(f'Completed upload {upload_id}: document {result["document_id"]}')
        
        return result

    @http.route('/office/upload/resume', type='json', auth='user')
    def upload_resume(self, upload_id, **kwargs):
        """Get upload status for resume.
        
        Args:
            upload_id: Upload session ID
            
        Returns:
            List of already uploaded chunk indices
        """
        upload_dir = os.path.join(UPLOAD_TEMP_DIR, upload_id)
        
        if not os.path.exists(upload_dir):
            return {'exists': False}
        
        with open(os.path.join(upload_dir, 'metadata.json'), 'r') as f:
            metadata = json.load(f)
        
        return {
            'exists': True,
            'chunks_received': sorted(metadata['chunks_received']),
            'total_chunks': metadata['total_chunks'],
            'filename': metadata['filename'],
        }

    @http.route('/office/upload/cancel', type='json', auth='user')
    def upload_cancel(self, upload_id, **kwargs):
        """Cancel an upload session."""
        upload_dir = os.path.join(UPLOAD_TEMP_DIR, upload_id)
        
        if os.path.exists(upload_dir):
            import shutil
            shutil.rmtree(upload_dir, ignore_errors=True)
        
        return {'success': True}

    # =========================================================================
    # FOLDER UPLOAD
    # =========================================================================

    @http.route('/office/upload/folder', type='json', auth='user')
    def upload_folder(self, folder_name, files, parent_folder_id=False, **kwargs):
        """Upload an entire folder structure.
        
        Args:
            folder_name: Root folder name
            files: List of {path: relative_path, data: base64_data, name: filename}
            parent_folder_id: Optional parent folder
            
        Returns:
            Created folder info
        """
        Folder = request.env['office.folder']
        Document = request.env['office.document']
        
        # Create root folder
        root_folder = Folder.create_folder(folder_name, parent_folder_id)
        created_folders = {'/': root_folder['id']}
        
        # Process files
        for file_info in files:
            rel_path = file_info.get('path', '')
            filename = file_info.get('name', 'unnamed')
            file_data = file_info.get('data', '')
            
            # Create intermediate folders
            path_parts = rel_path.split('/')[:-1]  # Exclude filename
            current_parent = root_folder['id']
            current_path = '/'
            
            for part in path_parts:
                if not part:
                    continue
                current_path = f'{current_path}{part}/'
                
                if current_path not in created_folders:
                    new_folder = Folder.create_folder(part, current_parent)
                    created_folders[current_path] = new_folder['id']
                
                current_parent = created_folders[current_path]
            
            # Upload file
            if file_data:
                Document.upload_document(
                    filename,
                    file_data,
                    current_parent
                )
        
        return {
            'folder_id': root_folder['id'],
            'folder_name': folder_name,
            'file_count': len(files),
        }

    # =========================================================================
    # DOCUMENT OPERATIONS (JSON API)
    # =========================================================================

    @http.route('/office/api/document/create', type='json', auth='user')
    def api_create_document(self, doc_type, folder_id=False, name=None, **kwargs):
        """Create new document from template."""
        return request.env['office.document'].create_document_from_template(
            doc_type, folder_id, name
        )

    @http.route('/office/api/document/rename', type='json', auth='user')
    def api_rename_document(self, document_id, new_name, **kwargs):
        """Rename document."""
        doc = request.env['office.document'].browse(document_id)
        return doc.action_rename(new_name)

    @http.route('/office/api/document/move', type='json', auth='user')
    def api_move_document(self, document_id, folder_id=False, **kwargs):
        """Move document to folder."""
        return request.env['office.document'].move_document(document_id, folder_id)

    @http.route('/office/api/document/star', type='json', auth='user')
    def api_toggle_star(self, document_id, **kwargs):
        """Toggle star on document."""
        doc = request.env['office.document'].browse(document_id)
        return doc.action_toggle_star()

    @http.route('/office/api/document/trash', type='json', auth='user')
    def api_trash_document(self, document_id, **kwargs):
        """Move document to trash."""
        doc = request.env['office.document'].browse(document_id)
        doc.action_move_to_trash()
        return {'success': True}

    @http.route('/office/api/document/restore', type='json', auth='user')
    def api_restore_document(self, document_id, **kwargs):
        """Restore document from trash."""
        doc = request.env['office.document'].browse(document_id)
        doc.action_restore_from_trash()
        return {'success': True}

    @http.route('/office/api/document/duplicate', type='json', auth='user')
    def api_duplicate_document(self, document_id, **kwargs):
        """Duplicate document."""
        doc = request.env['office.document'].browse(document_id)
        return doc.action_duplicate()

    # =========================================================================
    # SHARING API
    # =========================================================================

    @http.route('/office/api/share/access_list', type='json', auth='user')
    def api_get_access_list(self, target_type, target_id, **kwargs):
        """Get list of users with access."""
        return request.env['office.document.access'].get_access_list(
            target_type, int(target_id)
        )

    @http.route('/office/api/share/grant', type='json', auth='user')
    def api_grant_access(self, target_type, target_id, user_id, permission='viewer', **kwargs):
        """Grant access to user."""
        access = request.env['office.document.access'].grant_access(
            target_type, int(target_id), int(user_id), permission
        )
        return {'success': True, 'access_id': access.id}

    @http.route('/office/api/share/revoke', type='json', auth='user')
    def api_revoke_access(self, target_type, target_id, user_id, **kwargs):
        """Revoke access from user."""
        request.env['office.document.access'].revoke_access(
            target_type, int(target_id), int(user_id)
        )
        return {'success': True}

    @http.route('/office/api/share/link', type='json', auth='user')
    def api_get_share_link(self, target_type, target_id, **kwargs):
        """Get or create share link."""
        if target_type == 'document':
            target = request.env['office.document'].browse(int(target_id))
            return target.get_share_link_info()
        else:
            # TODO: Folder share link
            return {}

    @http.route('/office/api/share/link/update', type='json', auth='user')
    def api_update_share_link(self, target_type, target_id, permission='viewer', 
                               active=True, allow_download=True, **kwargs):
        """Update share link settings."""
        if target_type == 'document':
            target = request.env['office.document'].browse(int(target_id))
            return target.update_share_link(
                permission=permission,
                active=active,
                allow_download=allow_download
            )
        return {}

    # =========================================================================
    # FOLDER API
    # =========================================================================

    @http.route('/office/api/folder/create', type='json', auth='user')
    def api_create_folder(self, name, parent_id=False, **kwargs):
        """Create new folder."""
        return request.env['office.folder'].create_folder(name, parent_id)

    @http.route('/office/api/folder/rename', type='json', auth='user')
    def api_rename_folder(self, folder_id, new_name, **kwargs):
        """Rename folder."""
        folder = request.env['office.folder'].browse(int(folder_id))
        return folder.action_rename(new_name)

    @http.route('/office/api/folder/move', type='json', auth='user')
    def api_move_folder(self, folder_id, target_parent_id=False, **kwargs):
        """Move folder."""
        folder = request.env['office.folder'].browse(int(folder_id))
        return folder.action_move(target_parent_id)

    @http.route('/office/api/folder/color', type='json', auth='user')
    def api_set_folder_color(self, folder_id, color, **kwargs):
        """Set folder color."""
        folder = request.env['office.folder'].browse(int(folder_id))
        return folder.action_set_color(color)

    @http.route('/office/api/folder/trash', type='json', auth='user')
    def api_trash_folder(self, folder_id, **kwargs):
        """Move folder to trash."""
        folder = request.env['office.folder'].browse(int(folder_id))
        return folder.action_move_to_trash()

    @http.route('/office/api/folder/tree', type='json', auth='user')
    def api_get_folder_tree(self, **kwargs):
        """Get folder tree."""
        return request.env['office.folder'].get_folder_tree()

    @http.route('/office/api/folder/colors', type='json', auth='user')
    def api_get_folder_colors(self, **kwargs):
        """Get available folder colors."""
        return request.env['office.folder'].get_folder_colors()

    # =========================================================================
    # DASHBOARD DATA
    # =========================================================================

    @http.route('/office/api/dashboard', type='json', auth='user')
    def api_get_dashboard_data(self, folder_id=False, filter=None, **kwargs):
        """Get all dashboard data in single call."""
        if filter:
            # Handle special views
            return request.env['office.document'].get_dashboard_data_by_filter(filter)
        return request.env['office.document'].get_dashboard_data(folder_id)

    # =========================================================================
    # VERSION HISTORY
    # =========================================================================

    @http.route('/office/api/versions', type='json', auth='user')
    def api_get_versions(self, document_id, **kwargs):
        """Get version history."""
        return request.env['office.document.version'].get_version_history(int(document_id))

    @http.route('/office/api/versions/restore', type='json', auth='user')
    def api_restore_version(self, version_id, **kwargs):
        """Restore a version."""
        version = request.env['office.document.version'].browse(int(version_id))
        return version.restore()

    # =========================================================================
    # ACTIVITY LOG
    # =========================================================================

    @http.route('/office/api/activity', type='json', auth='user')
    def api_get_activity(self, target_type, target_id, limit=50, **kwargs):
        """Get activity log."""
        return request.env['office.document.activity'].get_activity_log(
            target_type, int(target_id), limit
        )

    # =========================================================================
    # SEARCH
    # =========================================================================

    @http.route('/office/api/search', type='json', auth='user')
    def api_search(self, query, filters=None, **kwargs):
        """Search documents."""
        return request.env['office.document'].search_documents(query, filters)

    # =========================================================================
    # COMMENTS
    # =========================================================================

    @http.route('/office/api/comments', type='json', auth='user')
    def api_get_comments(self, document_id, include_resolved=False, **kwargs):
        """Get document comments."""
        return request.env['office.document.comment'].get_comments(
            int(document_id), include_resolved
        )

    @http.route('/office/api/comments/add', type='json', auth='user')
    def api_add_comment(self, document_id, content, parent_id=None, **kwargs):
        """Add comment to document."""
        comment = request.env['office.document.comment'].add_comment(
            int(document_id), content, parent_id
        )
        return {'id': comment.id}

    @http.route('/office/api/comments/resolve', type='json', auth='user')
    def api_resolve_comment(self, comment_id, **kwargs):
        """Resolve a comment."""
        comment = request.env['office.document.comment'].browse(int(comment_id))
        comment.resolve()
        return {'success': True}

    # =========================================================================
    # USER SEARCH (for sharing)
    # =========================================================================

    @http.route('/office/api/users/search', type='json', auth='user')
    def api_search_users(self, query, exclude_ids=None, limit=10, **kwargs):
        """Search users for sharing.
        
        Args:
            query: Search string (min 2 chars)
            exclude_ids: List of user IDs to exclude
            limit: Max results (default 10)
            
        Returns:
            List of user dicts with id, name, email, avatar
        """
        if not query or len(query) < 2:
            return []
        
        exclude_ids = exclude_ids or []
        # Always exclude current user and portal/public users
        exclude_ids.append(request.env.user.id)
        
        domain = [
            ('share', '=', False),
            ('id', 'not in', exclude_ids),
            '|',
            ('name', 'ilike', query),
            ('email', 'ilike', query),
        ]
        
        users = request.env['res.users'].search(domain, limit=limit)
        
        return [{
            'id': u.id,
            'name': u.name,
            'email': u.email or u.login,
            'login': u.login,
            'avatar': f'/web/image/res.users/{u.id}/avatar_128',
        } for u in users]
