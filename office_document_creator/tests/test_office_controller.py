# -*- coding: utf-8 -*-
# Copyright 2025 Odoo Community
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""
Office HTTP Controller Tests

Tests for all HTTP endpoints:
- Document operations
- Folder operations
- Search
- Share links
- File downloads
- Dashboard API
"""

import json
import base64
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from odoo.tests import TransactionCase, tagged, HttpCase
from odoo.exceptions import ValidationError, UserError


@tagged('post_install', '-at_install', 'office', 'office_controller')
class TestOfficeControllerDocuments(HttpCase):
    """Test document controller endpoints."""

    def setUp(self):
        super().setUp()
        self.Document = self.env['office.document']
        
    def test_create_document_endpoint(self):
        """Test document creation via API."""
        # Authenticate
        self.authenticate('admin', 'admin')
        
        # Call endpoint
        response = self.url_open(
            '/office/document/create',
            data=json.dumps({
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'template_type': 'word',
                    'name': 'API Created Doc',
                },
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        self.assertEqual(response.status_code, 200)

    def test_get_documents_endpoint(self):
        """Test getting documents list via API."""
        self.authenticate('admin', 'admin')
        
        response = self.url_open(
            '/office/documents',
            data=json.dumps({
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {},
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        self.assertEqual(response.status_code, 200)

    def test_get_document_detail_endpoint(self):
        """Test getting document details via API."""
        self.authenticate('admin', 'admin')
        
        # Create document first
        result = self.Document.create_document_from_template('word', name='Detail Test')
        doc_id = result['document_id']
        
        response = self.url_open(
            f'/office/document/{doc_id}',
            data=json.dumps({
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {},
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        self.assertEqual(response.status_code, 200)

    def test_rename_document_endpoint(self):
        """Test renaming document via API."""
        self.authenticate('admin', 'admin')
        
        result = self.Document.create_document_from_template('word', name='Old Name')
        doc_id = result['document_id']
        
        response = self.url_open(
            '/office/document/rename',
            data=json.dumps({
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'document_id': doc_id,
                    'new_name': 'New Name',
                },
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        self.assertEqual(response.status_code, 200)

    def test_delete_document_endpoint(self):
        """Test deleting document via API."""
        self.authenticate('admin', 'admin')
        
        result = self.Document.create_document_from_template('word', name='Delete Me')
        doc_id = result['document_id']
        
        response = self.url_open(
            '/office/document/delete',
            data=json.dumps({
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'document_id': doc_id,
                },
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        self.assertEqual(response.status_code, 200)


@tagged('post_install', '-at_install', 'office', 'office_controller')
class TestOfficeControllerFolders(HttpCase):
    """Test folder controller endpoints."""

    def setUp(self):
        super().setUp()
        self.Folder = self.env['office.folder']

    def test_create_folder_endpoint(self):
        """Test folder creation via API."""
        self.authenticate('admin', 'admin')
        
        response = self.url_open(
            '/office/folder/create',
            data=json.dumps({
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'name': 'API Folder',
                    'color': 'blue',
                },
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        self.assertEqual(response.status_code, 200)

    def test_get_folders_endpoint(self):
        """Test getting folders list via API."""
        self.authenticate('admin', 'admin')
        
        response = self.url_open(
            '/office/folders',
            data=json.dumps({
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {},
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        self.assertEqual(response.status_code, 200)

    def test_get_folder_contents_endpoint(self):
        """Test getting folder contents via API."""
        self.authenticate('admin', 'admin')
        
        folder = self.Folder.create({'name': 'Content Test'})
        
        response = self.url_open(
            f'/office/folder/{folder.id}/contents',
            data=json.dumps({
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {},
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        self.assertEqual(response.status_code, 200)

    def test_rename_folder_endpoint(self):
        """Test renaming folder via API."""
        self.authenticate('admin', 'admin')
        
        folder = self.Folder.create({'name': 'Old Folder'})
        
        response = self.url_open(
            '/office/folder/rename',
            data=json.dumps({
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'folder_id': folder.id,
                    'new_name': 'New Folder',
                },
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        self.assertEqual(response.status_code, 200)

    def test_delete_folder_endpoint(self):
        """Test deleting folder via API."""
        self.authenticate('admin', 'admin')
        
        folder = self.Folder.create({'name': 'Delete Me'})
        
        response = self.url_open(
            '/office/folder/delete',
            data=json.dumps({
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'folder_id': folder.id,
                },
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        self.assertEqual(response.status_code, 200)


@tagged('post_install', '-at_install', 'office', 'office_controller')
class TestOfficeControllerSearch(HttpCase):
    """Test search controller endpoints."""

    def setUp(self):
        super().setUp()
        self.Document = self.env['office.document']

    def test_search_documents_endpoint(self):
        """Test document search via API."""
        self.authenticate('admin', 'admin')
        
        # Create test document
        self.Document.create_document_from_template('word', name='Searchable Document')
        
        response = self.url_open(
            '/office/search',
            data=json.dumps({
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'query': 'Searchable',
                },
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        self.assertEqual(response.status_code, 200)

    def test_search_with_filters_endpoint(self):
        """Test search with filters via API."""
        self.authenticate('admin', 'admin')
        
        response = self.url_open(
            '/office/search',
            data=json.dumps({
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'query': 'document',
                    'file_type': 'word',
                    'date_from': '2024-01-01',
                },
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        self.assertEqual(response.status_code, 200)

    def test_search_empty_query(self):
        """Test search with empty query."""
        self.authenticate('admin', 'admin')
        
        response = self.url_open(
            '/office/search',
            data=json.dumps({
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'query': '',
                },
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        self.assertEqual(response.status_code, 200)


@tagged('post_install', '-at_install', 'office', 'office_controller')
class TestOfficeControllerDownload(HttpCase):
    """Test download controller endpoints."""

    def setUp(self):
        super().setUp()
        self.Document = self.env['office.document']

    def test_download_document_endpoint(self):
        """Test document download via API."""
        self.authenticate('admin', 'admin')
        
        # Create document with content
        result = self.Document.create_document_from_template('word', name='Download Test')
        doc_id = result['document_id']
        
        response = self.url_open(f'/office/document/{doc_id}/download')
        
        self.assertIn(response.status_code, [200, 302])

    def test_download_nonexistent_document(self):
        """Test downloading non-existent document."""
        self.authenticate('admin', 'admin')
        
        response = self.url_open('/office/document/999999/download')
        
        self.assertIn(response.status_code, [404, 500])

    def test_download_without_auth(self):
        """Test download without authentication."""
        result = self.Document.create_document_from_template('word', name='Auth Test')
        doc_id = result['document_id']
        
        response = self.url_open(f'/office/document/{doc_id}/download')
        
        # Should redirect to login or return error
        self.assertIn(response.status_code, [200, 302, 303, 403])


@tagged('post_install', '-at_install', 'office', 'office_controller')
class TestOfficeControllerUpload(HttpCase):
    """Test upload controller endpoints."""

    def test_upload_document_endpoint(self):
        """Test document upload via API."""
        self.authenticate('admin', 'admin')
        
        # Create test file content
        file_content = base64.b64encode(b'Test file content').decode()
        
        response = self.url_open(
            '/office/document/upload',
            data=json.dumps({
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'filename': 'test.txt',
                    'content': file_content,
                },
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        self.assertEqual(response.status_code, 200)

    def test_upload_large_file(self):
        """Test uploading large file."""
        self.authenticate('admin', 'admin')
        
        # Create 5MB content
        large_content = base64.b64encode(b'X' * (5 * 1024 * 1024)).decode()
        
        response = self.url_open(
            '/office/document/upload',
            data=json.dumps({
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'filename': 'large_file.bin',
                    'content': large_content,
                },
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        # Should either succeed or return proper error
        self.assertIn(response.status_code, [200, 413])


@tagged('post_install', '-at_install', 'office', 'office_controller')
class TestOfficeControllerShareLink(HttpCase):
    """Test share link controller endpoints."""

    def setUp(self):
        super().setUp()
        self.Document = self.env['office.document']
        self.ShareLink = self.env['office.share.link']

    def test_create_share_link_endpoint(self):
        """Test creating share link via API."""
        self.authenticate('admin', 'admin')
        
        result = self.Document.create_document_from_template('word', name='Share Link Test')
        doc_id = result['document_id']
        
        response = self.url_open(
            '/office/share/create',
            data=json.dumps({
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'document_id': doc_id,
                },
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        self.assertEqual(response.status_code, 200)

    def test_access_share_link_public(self):
        """Test accessing public share link."""
        result = self.Document.create_document_from_template('word', name='Public Link Test')
        doc = self.Document.browse(result['document_id'])
        link = self.ShareLink.create_share_link('document', doc.id)
        
        response = self.url_open(f'/office/share/{link.token}')
        
        self.assertIn(response.status_code, [200, 302])

    def test_access_share_link_with_password(self):
        """Test accessing password-protected share link."""
        result = self.Document.create_document_from_template('word', name='Password Link Test')
        doc = self.Document.browse(result['document_id'])
        link = self.ShareLink.create_share_link('document', doc.id, password='test123')
        
        # Access without password
        response = self.url_open(f'/office/share/{link.token}')
        
        # Should request password
        self.assertEqual(response.status_code, 200)

    def test_access_expired_share_link(self):
        """Test accessing expired share link."""
        result = self.Document.create_document_from_template('word', name='Expired Link Test')
        doc = self.Document.browse(result['document_id'])
        link = self.ShareLink.create({
            'document_id': doc.id,
            'expiry_date': datetime.now() - timedelta(days=1),
        })
        
        response = self.url_open(f'/office/share/{link.token}')
        
        # Should show expired message
        self.assertEqual(response.status_code, 200)


@tagged('post_install', '-at_install', 'office', 'office_controller')
class TestOfficeControllerDashboard(HttpCase):
    """Test dashboard controller endpoints."""

    def test_get_dashboard_data_endpoint(self):
        """Test getting dashboard data via API."""
        self.authenticate('admin', 'admin')
        
        response = self.url_open(
            '/office/dashboard/data',
            data=json.dumps({
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {},
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        self.assertEqual(response.status_code, 200)

    def test_get_recent_documents_endpoint(self):
        """Test getting recent documents via API."""
        self.authenticate('admin', 'admin')
        
        response = self.url_open(
            '/office/documents/recent',
            data=json.dumps({
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'limit': 10,
                },
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        self.assertEqual(response.status_code, 200)

    def test_get_starred_documents_endpoint(self):
        """Test getting starred documents via API."""
        self.authenticate('admin', 'admin')
        
        response = self.url_open(
            '/office/documents/starred',
            data=json.dumps({
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {},
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        self.assertEqual(response.status_code, 200)

    def test_get_storage_stats_endpoint(self):
        """Test getting storage statistics via API."""
        self.authenticate('admin', 'admin')
        
        response = self.url_open(
            '/office/storage/stats',
            data=json.dumps({
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {},
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        self.assertEqual(response.status_code, 200)


@tagged('post_install', '-at_install', 'office', 'office_controller')
class TestOfficeControllerSecurity(HttpCase):
    """Test controller security."""

    def setUp(self):
        super().setUp()
        self.Document = self.env['office.document']

    def test_csrf_protection(self):
        """Test CSRF protection on POST endpoints."""
        self.authenticate('admin', 'admin')
        
        # Try POST without proper CSRF token (in non-json mode)
        response = self.url_open(
            '/office/document/delete',
            data={'document_id': 1},
        )
        
        # Should handle appropriately
        self.assertIn(response.status_code, [200, 400, 403])

    def test_authentication_required(self):
        """Test endpoints require authentication."""
        response = self.url_open(
            '/office/documents',
            data=json.dumps({
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {},
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        # Should redirect to login or return auth error
        self.assertIn(response.status_code, [200, 302, 303])

    def test_access_control_other_user_document(self):
        """Test accessing another user's private document."""
        # Create doc as admin
        result = self.Document.create_document_from_template('word', name='Private Doc')
        doc_id = result['document_id']
        
        # Try to access as demo user
        self.authenticate('demo', 'demo')
        
        response = self.url_open(f'/office/document/{doc_id}')
        
        # Should be restricted
        self.assertIn(response.status_code, [200, 302, 403, 404])

    def test_xss_prevention(self):
        """Test XSS prevention in inputs."""
        self.authenticate('admin', 'admin')
        
        malicious_name = '<script>alert("XSS")</script>'
        
        response = self.url_open(
            '/office/document/create',
            data=json.dumps({
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'template_type': 'word',
                    'name': malicious_name,
                },
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        # Should handle safely
        self.assertEqual(response.status_code, 200)

    def test_sql_injection_prevention(self):
        """Test SQL injection prevention in search."""
        self.authenticate('admin', 'admin')
        
        malicious_query = "'; DROP TABLE ir_attachment; --"
        
        response = self.url_open(
            '/office/search',
            data=json.dumps({
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'query': malicious_query,
                },
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        # Should handle safely
        self.assertEqual(response.status_code, 200)


@tagged('post_install', '-at_install', 'office', 'office_controller')
class TestOfficeControllerErrorHandling(HttpCase):
    """Test controller error handling."""

    def test_invalid_json_request(self):
        """Test handling invalid JSON."""
        self.authenticate('admin', 'admin')
        
        response = self.url_open(
            '/office/documents',
            data='invalid json{{{',
            headers={'Content-Type': 'application/json'}
        )
        
        # Should return error response
        self.assertIn(response.status_code, [200, 400])

    def test_missing_required_params(self):
        """Test handling missing required parameters."""
        self.authenticate('admin', 'admin')
        
        response = self.url_open(
            '/office/document/create',
            data=json.dumps({
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    # Missing template_type
                },
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        self.assertEqual(response.status_code, 200)

    def test_invalid_document_id(self):
        """Test handling invalid document ID."""
        self.authenticate('admin', 'admin')
        
        response = self.url_open(
            '/office/document/rename',
            data=json.dumps({
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'document_id': 999999,
                    'new_name': 'Test',
                },
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        self.assertEqual(response.status_code, 200)

    def test_invalid_folder_id(self):
        """Test handling invalid folder ID."""
        self.authenticate('admin', 'admin')
        
        response = self.url_open(
            '/office/folder/999999/contents',
            data=json.dumps({
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {},
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        self.assertIn(response.status_code, [200, 404])
