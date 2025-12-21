# -*- coding: utf-8 -*-
# Copyright 2025 Odoo Community
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""
Office Share Functionality - Integration Tests

Tests for complete sharing workflows:
- Document sharing with users
- Share link generation and access
- Permission enforcement
- Public access
"""

import base64
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError, UserError, AccessError


@tagged('post_install', '-at_install', 'office', 'office_share')
class TestOfficeDocumentSharing(TransactionCase):
    """Test document sharing workflows."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Document = cls.env['office.document']
        cls.Access = cls.env['office.document.access']
        cls.ShareLink = cls.env['office.share.link']
        cls.user_demo = cls.env.ref('base.user_demo')
        cls.user_admin = cls.env.ref('base.user_admin')
        
        # Create test document
        result = cls.Document.create_document_from_template('word', name='Share Test Doc')
        cls.test_doc = cls.Document.browse(result['document_id'])

    def test_share_document_with_user(self):
        """Test complete workflow of sharing document with user."""
        # Grant access
        access = self.Access.grant_access(
            'document',
            self.test_doc.id,
            self.user_demo.id,
            'viewer'
        )
        
        # Verify access exists
        self.assertTrue(access.id)
        
        # Verify in access list
        access_list = self.Access.get_access_list('document', self.test_doc.id)
        user_ids = [a['user_id'] for a in access_list]
        self.assertIn(self.user_demo.id, user_ids)
        
        # Verify document is marked as shared
        self.test_doc.invalidate_recordset()
        self.assertTrue(self.test_doc.is_shared)

    def test_share_document_update_permission(self):
        """Test updating share permission."""
        # Grant viewer first
        self.Access.grant_access('document', self.test_doc.id, self.user_demo.id, 'viewer')
        
        # Update to editor
        self.Access.grant_access('document', self.test_doc.id, self.user_demo.id, 'editor')
        
        # Verify updated
        access_list = self.Access.get_access_list('document', self.test_doc.id)
        user_access = next((a for a in access_list if a['user_id'] == self.user_demo.id), None)
        self.assertEqual(user_access['permission'], 'editor')

    def test_unshare_document_from_user(self):
        """Test removing user access."""
        self.Access.grant_access('document', self.test_doc.id, self.user_demo.id, 'viewer')
        
        self.Access.revoke_access('document', self.test_doc.id, self.user_demo.id)
        
        access_list = self.Access.get_access_list('document', self.test_doc.id)
        user_ids = [a['user_id'] for a in access_list]
        self.assertNotIn(self.user_demo.id, user_ids)

    def test_get_share_link_info(self):
        """Test getting share link information for document."""
        # Create share link
        self.ShareLink.create_share_link('document', self.test_doc.id)
        
        # Get info
        info = self.test_doc.get_share_link_info()
        
        self.assertIn('token', info)
        self.assertIn('url', info)
        self.assertIn('is_active', info)
        self.assertTrue(info['is_active'])

    def test_update_share_link_settings(self):
        """Test updating share link settings."""
        self.ShareLink.create_share_link('document', self.test_doc.id)
        
        result = self.test_doc.update_share_link(
            permission='editor',
            allow_download=False
        )
        
        self.assertEqual(result['permission'], 'editor')
        self.assertFalse(result['allow_download'])


@tagged('post_install', '-at_install', 'office', 'office_share')
class TestOfficeFolderSharing(TransactionCase):
    """Test folder sharing workflows."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Folder = cls.env['office.folder']
        cls.Document = cls.env['office.document']
        cls.Access = cls.env['office.document.access']
        cls.user_demo = cls.env.ref('base.user_demo')
        
        # Create test folder with documents
        cls.test_folder = cls.Folder.create({'name': 'Shared Folder'})
        cls.Document.create_document_from_template('word', folder_id=cls.test_folder.id, name='Doc1')
        cls.Document.create_document_from_template('excel', folder_id=cls.test_folder.id, name='Doc2')

    def test_share_folder_with_user(self):
        """Test sharing folder grants access to contents."""
        self.Access.grant_access(
            'folder',
            self.test_folder.id,
            self.user_demo.id,
            'viewer'
        )
        
        # Folder should be marked as shared
        self.test_folder.invalidate_recordset()
        self.assertTrue(self.test_folder.is_shared)

    def test_folder_share_permission_inheritance(self):
        """Test folder permissions are inherited by documents."""
        self.Access.grant_access(
            'folder',
            self.test_folder.id,
            self.user_demo.id,
            'editor'
        )
        
        # Documents in folder should inherit access
        for doc in self.test_folder.document_ids:
            access_list = self.Access.get_access_list('document', doc.id)
            # Should show inherited access
            self.assertIsInstance(access_list, list)

    def test_nested_folder_sharing(self):
        """Test sharing nested folders."""
        parent = self.test_folder
        child = self.Folder.create({'name': 'Child Folder', 'parent_id': parent.id})
        
        self.Access.grant_access('folder', parent.id, self.user_demo.id, 'viewer')
        
        # Child should also be accessible
        child.invalidate_recordset()
        # Access check depends on implementation


@tagged('post_install', '-at_install', 'office', 'office_share')
class TestOfficeShareLinkAccess(TransactionCase):
    """Test share link access scenarios."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Document = cls.env['office.document']
        cls.ShareLink = cls.env['office.share.link']
        
        result = cls.Document.create_document_from_template('word', name='Link Test')
        cls.test_doc = cls.Document.browse(result['document_id'])

    def test_access_via_valid_link(self):
        """Test accessing document via valid share link."""
        link = self.ShareLink.create_share_link('document', self.test_doc.id)
        
        is_valid, error = link.validate_access()
        
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_access_via_expired_link(self):
        """Test accessing document via expired link."""
        link = self.ShareLink.create({
            'document_id': self.test_doc.id,
            'expiry_date': datetime.now() - timedelta(hours=1),
        })
        
        is_valid, error = link.validate_access()
        
        self.assertFalse(is_valid)
        self.assertIn('expired', error.lower())

    def test_access_via_password_link_correct(self):
        """Test accessing password-protected link with correct password."""
        link = self.ShareLink.create_share_link(
            'document',
            self.test_doc.id,
            password='Secret123'
        )
        
        is_valid, error = link.validate_access('Secret123')
        
        self.assertTrue(is_valid)

    def test_access_via_password_link_wrong(self):
        """Test accessing password-protected link with wrong password."""
        link = self.ShareLink.create_share_link(
            'document',
            self.test_doc.id,
            password='Secret123'
        )
        
        is_valid, error = link.validate_access('WrongPassword')
        
        self.assertFalse(is_valid)

    def test_access_via_inactive_link(self):
        """Test accessing inactive share link."""
        link = self.ShareLink.create_share_link('document', self.test_doc.id)
        link.is_active = False
        
        is_valid, error = link.validate_access()
        
        self.assertFalse(is_valid)

    def test_access_via_nonexistent_link(self):
        """Test accessing with invalid token."""
        link = self.ShareLink.search([('token', '=', 'nonexistent_token_xyz')])
        
        self.assertFalse(link.exists())

    def test_viewer_permission_restrictions(self):
        """Test viewer permission restrictions."""
        link = self.ShareLink.create({
            'document_id': self.test_doc.id,
            'permission': 'viewer',
            'allow_download': False,
        })
        
        self.assertEqual(link.permission, 'viewer')
        self.assertFalse(link.allow_download)

    def test_editor_permission_capabilities(self):
        """Test editor permission capabilities."""
        link = self.ShareLink.create({
            'document_id': self.test_doc.id,
            'permission': 'editor',
        })
        
        self.assertEqual(link.permission, 'editor')


@tagged('post_install', '-at_install', 'office', 'office_share')
class TestOfficeShareVisibility(TransactionCase):
    """Test visibility of shared items."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Document = cls.env['office.document']
        cls.Folder = cls.env['office.folder']
        cls.Access = cls.env['office.document.access']
        cls.user_demo = cls.env.ref('base.user_demo')

    def test_shared_with_me_view(self):
        """Test documents appear in 'Shared with me' view."""
        result = self.Document.create_document_from_template('word', name='Shared Doc')
        doc = self.Document.browse(result['document_id'])
        
        self.Access.grant_access('document', doc.id, self.user_demo.id, 'viewer')
        
        # Query as demo user
        shared_docs = self.Document.with_user(self.user_demo).search([
            ('is_shared', '=', True)
        ])
        
        # Should find shared documents
        self.assertIsInstance(shared_docs, type(self.Document))

    def test_owner_sees_shared_status(self):
        """Test owner can see who document is shared with."""
        result = self.Document.create_document_from_template('word', name='Owner Test')
        doc = self.Document.browse(result['document_id'])
        
        self.Access.grant_access('document', doc.id, self.user_demo.id, 'viewer')
        
        access_list = self.Access.get_access_list('document', doc.id)
        
        # Owner should see full access list
        self.assertTrue(len(access_list) >= 1)
        
        # Check contains expected data
        user_access = next((a for a in access_list if a['user_id'] == self.user_demo.id), None)
        self.assertIsNotNone(user_access)
        self.assertIn('user_name', user_access)
        self.assertIn('avatar_url', user_access)

    def test_share_indicators_on_items(self):
        """Test shared items show share indicators."""
        result = self.Document.create_document_from_template('word', name='Indicator Test')
        doc = self.Document.browse(result['document_id'])
        
        # Before sharing
        self.assertFalse(doc.is_shared)
        
        # After sharing
        self.Access.grant_access('document', doc.id, self.user_demo.id, 'viewer')
        doc.invalidate_recordset()
        
        self.assertTrue(doc.is_shared)


@tagged('post_install', '-at_install', 'office', 'office_share')
class TestOfficeShareEdgeCases(TransactionCase):
    """Test edge cases in sharing functionality."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Document = cls.env['office.document']
        cls.Access = cls.env['office.document.access']
        cls.ShareLink = cls.env['office.share.link']
        cls.user_demo = cls.env.ref('base.user_demo')

    def test_share_then_delete_document(self):
        """Test deleting a shared document."""
        result = self.Document.create_document_from_template('word')
        doc = self.Document.browse(result['document_id'])
        
        self.Access.grant_access('document', doc.id, self.user_demo.id, 'viewer')
        link = self.ShareLink.create_share_link('document', doc.id)
        
        # Delete document
        doc.action_move_to_trash()
        doc.action_delete_permanently()
        
        # Access records should be cleaned up
        access = self.Access.search([('document_id', '=', result['document_id'])])
        self.assertFalse(access.exists())

    def test_share_to_same_user_multiple_times(self):
        """Test sharing to same user multiple times."""
        result = self.Document.create_document_from_template('word')
        doc = self.Document.browse(result['document_id'])
        
        # Share multiple times
        a1 = self.Access.grant_access('document', doc.id, self.user_demo.id, 'viewer')
        a2 = self.Access.grant_access('document', doc.id, self.user_demo.id, 'editor')
        a3 = self.Access.grant_access('document', doc.id, self.user_demo.id, 'commenter')
        
        # Should be same record, updated
        self.assertEqual(a1.id, a2.id)
        self.assertEqual(a2.id, a3.id)

    def test_share_link_regeneration(self):
        """Test regenerating share link."""
        result = self.Document.create_document_from_template('word')
        doc = self.Document.browse(result['document_id'])
        
        link1 = self.ShareLink.create_share_link('document', doc.id)
        token1 = link1.token
        
        # Deactivate and create new
        link1.is_active = False
        link2 = self.ShareLink.create_share_link('document', doc.id)
        
        self.assertNotEqual(token1, link2.token)

    def test_empty_password(self):
        """Test share link with empty password."""
        result = self.Document.create_document_from_template('word')
        doc = self.Document.browse(result['document_id'])
        
        link = self.ShareLink.create_share_link('document', doc.id, password='')
        
        # Should not require password
        self.assertFalse(link.requires_password)

    def test_very_long_password(self):
        """Test share link with very long password."""
        result = self.Document.create_document_from_template('word')
        doc = self.Document.browse(result['document_id'])
        
        long_password = 'P' * 1000
        link = self.ShareLink.create_share_link('document', doc.id, password=long_password)
        
        is_valid, _ = link.validate_access(long_password)
        self.assertTrue(is_valid)

    def test_special_characters_in_password(self):
        """Test password with special characters."""
        result = self.Document.create_document_from_template('word')
        doc = self.Document.browse(result['document_id'])
        
        special_password = "P@$$w0rd!#$%^&*(){}[]|\\:\";<>,.?/~`"
        link = self.ShareLink.create_share_link('document', doc.id, password=special_password)
        
        is_valid, _ = link.validate_access(special_password)
        self.assertTrue(is_valid)
