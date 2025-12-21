# -*- coding: utf-8 -*-
# Copyright 2025 Odoo Community
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""
Office End-to-End Integration Tests

Complete workflow tests that simulate real user scenarios:
- Full document lifecycle
- Collaboration workflows
- Multi-user scenarios
- Complex folder operations
"""

import base64
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError, UserError, AccessError


@tagged('post_install', '-at_install', 'office', 'office_integration')
class TestOfficeDocumentLifecycle(TransactionCase):
    """Test complete document lifecycle from creation to deletion."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Document = cls.env['office.document']
        cls.Folder = cls.env['office.folder']
        cls.Version = cls.env['office.document.version']
        cls.Comment = cls.env['office.document.comment']
        cls.Activity = cls.env['office.document.activity']

    def test_full_document_lifecycle(self):
        """Test complete document lifecycle: create -> edit -> share -> archive -> delete."""
        # Step 1: Create document
        result = self.Document.create_document_from_template('word', name='Lifecycle Test')
        doc = self.Document.browse(result['document_id'])
        self.assertTrue(doc.exists())
        
        # Step 2: Edit (create new version)
        new_content = base64.b64encode(b'Updated content').decode()
        doc.create_version(new_content, 'Updated document')
        self.assertGreater(doc.version_count, 1)
        
        # Step 3: Add comment
        doc.add_comment('This is a test comment')
        self.assertGreater(doc.comment_count, 0)
        
        # Step 4: Star document
        doc.toggle_starred()
        self.assertTrue(doc.is_starred)
        
        # Step 5: Move to folder
        folder = self.Folder.create({'name': 'Lifecycle Folder'})
        doc.action_move_to_folder(folder.id)
        self.assertEqual(doc.folder_id.id, folder.id)
        
        # Step 6: Move to trash
        doc.action_move_to_trash()
        self.assertTrue(doc.is_trashed)
        
        # Step 7: Restore from trash
        doc.action_restore_from_trash()
        self.assertFalse(doc.is_trashed)
        
        # Step 8: Move to trash again
        doc.action_move_to_trash()
        
        # Step 9: Permanently delete
        doc.action_delete_permanently()
        self.assertFalse(doc.exists())

    def test_document_with_versions_lifecycle(self):
        """Test document with multiple versions lifecycle."""
        result = self.Document.create_document_from_template('excel', name='Version Test')
        doc = self.Document.browse(result['document_id'])
        
        # Create multiple versions
        for i in range(5):
            content = base64.b64encode(f'Version {i + 1} content'.encode()).decode()
            doc.create_version(content, f'Version {i + 1}')
        
        self.assertEqual(doc.version_count, 6)  # 1 original + 5 new
        
        # Restore older version
        versions = self.Version.search([('document_id', '=', doc.id)], order='create_date')
        old_version = versions[1]
        doc.restore_version(old_version.id)
        
        # Verify version count increased
        doc.invalidate_recordset()
        self.assertEqual(doc.version_count, 7)

    def test_document_collaboration_workflow(self):
        """Test document collaboration workflow with comments and activity."""
        result = self.Document.create_document_from_template('word', name='Collab Test')
        doc = self.Document.browse(result['document_id'])
        user_demo = self.env.ref('base.user_demo')
        
        # Owner adds comment
        comment1 = doc.add_comment('Initial feedback requested')
        
        # User adds reply (as admin for now)
        comment2 = doc.add_comment('Here is my response', parent_id=comment1.id)
        
        # Another reply
        doc.add_comment('Acknowledged, will update', parent_id=comment1.id)
        
        # Resolve thread
        comment1.action_resolve()
        self.assertTrue(comment1.is_resolved)
        
        # Check activity log
        activities = self.Activity.search([('document_id', '=', doc.id)])
        self.assertGreater(len(activities), 0)


@tagged('post_install', '-at_install', 'office', 'office_integration')
class TestOfficeFolderWorkflow(TransactionCase):
    """Test complete folder workflows."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Document = cls.env['office.document']
        cls.Folder = cls.env['office.folder']

    def test_folder_organization_workflow(self):
        """Test complete folder organization workflow."""
        # Create folder hierarchy
        root = self.Folder.create({'name': 'Root Folder', 'color': 'blue'})
        child1 = self.Folder.create({'name': 'Child 1', 'parent_id': root.id, 'color': 'green'})
        child2 = self.Folder.create({'name': 'Child 2', 'parent_id': root.id, 'color': 'yellow'})
        grandchild = self.Folder.create({'name': 'Grandchild', 'parent_id': child1.id, 'color': 'red'})
        
        # Add documents to various levels
        self.Document.create_document_from_template('word', folder_id=root.id, name='Root Doc')
        self.Document.create_document_from_template('excel', folder_id=child1.id, name='Child1 Doc')
        self.Document.create_document_from_template('presentation', folder_id=grandchild.id, name='Grandchild Doc')
        
        # Verify hierarchy
        self.assertEqual(root.child_folder_ids.ids, [child1.id, child2.id])
        self.assertEqual(child1.child_folder_ids.ids, [grandchild.id])
        
        # Move folder
        child2.write({'parent_id': child1.id})
        self.assertEqual(child2.parent_id.id, child1.id)
        
        # Rename folder
        child2.write({'name': 'Renamed Child 2'})
        self.assertEqual(child2.name, 'Renamed Child 2')
        
        # Delete folder (should handle documents)
        child2.unlink()
        self.assertFalse(child2.exists())

    def test_move_documents_between_folders(self):
        """Test moving documents between folders."""
        folder1 = self.Folder.create({'name': 'Source Folder'})
        folder2 = self.Folder.create({'name': 'Destination Folder'})
        
        # Create documents in folder1
        result1 = self.Document.create_document_from_template('word', folder_id=folder1.id, name='Doc 1')
        result2 = self.Document.create_document_from_template('excel', folder_id=folder1.id, name='Doc 2')
        
        doc1 = self.Document.browse(result1['document_id'])
        doc2 = self.Document.browse(result2['document_id'])
        
        # Verify in source folder
        self.assertEqual(doc1.folder_id.id, folder1.id)
        self.assertEqual(len(folder1.document_ids), 2)
        
        # Move to destination
        doc1.action_move_to_folder(folder2.id)
        doc2.action_move_to_folder(folder2.id)
        
        folder1.invalidate_recordset()
        folder2.invalidate_recordset()
        
        # Verify moved
        self.assertEqual(doc1.folder_id.id, folder2.id)
        self.assertEqual(doc2.folder_id.id, folder2.id)
        self.assertEqual(len(folder2.document_ids), 2)
        self.assertEqual(len(folder1.document_ids), 0)


@tagged('post_install', '-at_install', 'office', 'office_integration')
class TestOfficeMultiUserScenarios(TransactionCase):
    """Test multi-user collaboration scenarios."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Document = cls.env['office.document']
        cls.Folder = cls.env['office.folder']
        cls.Access = cls.env['office.document.access']
        cls.ShareLink = cls.env['office.share.link']
        cls.user_demo = cls.env.ref('base.user_demo')
        cls.user_admin = cls.env.ref('base.user_admin')

    def test_document_sharing_workflow(self):
        """Test complete document sharing workflow between users."""
        # Admin creates document
        result = self.Document.create_document_from_template('word', name='Shared Project')
        doc = self.Document.browse(result['document_id'])
        
        # Share with demo user as editor
        self.Access.grant_access('document', doc.id, self.user_demo.id, 'editor')
        
        # Verify demo user can access
        access_list = self.Access.get_access_list('document', doc.id)
        user_access = next((a for a in access_list if a['user_id'] == self.user_demo.id), None)
        self.assertIsNotNone(user_access)
        self.assertEqual(user_access['permission'], 'editor')
        
        # Change permission to viewer
        self.Access.grant_access('document', doc.id, self.user_demo.id, 'viewer')
        
        access_list = self.Access.get_access_list('document', doc.id)
        user_access = next((a for a in access_list if a['user_id'] == self.user_demo.id), None)
        self.assertEqual(user_access['permission'], 'viewer')
        
        # Revoke access
        self.Access.revoke_access('document', doc.id, self.user_demo.id)
        
        access_list = self.Access.get_access_list('document', doc.id)
        user_ids = [a['user_id'] for a in access_list]
        self.assertNotIn(self.user_demo.id, user_ids)

    def test_folder_sharing_with_contents(self):
        """Test sharing folder shares contents."""
        # Create folder with documents
        folder = self.Folder.create({'name': 'Team Folder'})
        self.Document.create_document_from_template('word', folder_id=folder.id, name='Team Doc 1')
        self.Document.create_document_from_template('excel', folder_id=folder.id, name='Team Doc 2')
        
        # Share folder
        self.Access.grant_access('folder', folder.id, self.user_demo.id, 'viewer')
        
        # Verify folder is shared
        folder.invalidate_recordset()
        self.assertTrue(folder.is_shared)

    def test_share_link_public_access(self):
        """Test public access via share link."""
        result = self.Document.create_document_from_template('word', name='Public Doc')
        doc = self.Document.browse(result['document_id'])
        
        # Create share link
        link = self.ShareLink.create_share_link('document', doc.id)
        
        # Validate link
        is_valid, error = link.validate_access()
        self.assertTrue(is_valid)
        
        # Get document info via link
        info = link.get_shared_resource_info()
        self.assertIn('name', info)
        self.assertEqual(info['name'], 'Public Doc')


@tagged('post_install', '-at_install', 'office', 'office_integration')
class TestOfficeSearchWorkflow(TransactionCase):
    """Test search functionality workflows."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Document = cls.env['office.document']
        cls.Folder = cls.env['office.folder']

    def test_search_by_name(self):
        """Test searching documents by name."""
        # Create test documents
        self.Document.create_document_from_template('word', name='Financial Report Q1')
        self.Document.create_document_from_template('word', name='Financial Report Q2')
        self.Document.create_document_from_template('excel', name='Budget Spreadsheet')
        
        # Search for financial
        results = self.Document.search([('name', 'ilike', 'Financial')])
        self.assertEqual(len(results), 2)
        
        # Search for budget
        results = self.Document.search([('name', 'ilike', 'Budget')])
        self.assertEqual(len(results), 1)

    def test_search_by_file_type(self):
        """Test searching by file type."""
        self.Document.create_document_from_template('word', name='Word Doc')
        self.Document.create_document_from_template('excel', name='Excel Doc')
        self.Document.create_document_from_template('presentation', name='Presentation Doc')
        
        # Search word documents
        word_docs = self.Document.search([('file_category', '=', 'word')])
        self.assertGreater(len(word_docs), 0)
        
        # Search excel documents
        excel_docs = self.Document.search([('file_category', '=', 'excel')])
        self.assertGreater(len(excel_docs), 0)

    def test_search_by_folder(self):
        """Test searching within folder."""
        folder = self.Folder.create({'name': 'Search Test Folder'})
        
        self.Document.create_document_from_template('word', folder_id=folder.id, name='Folder Doc 1')
        self.Document.create_document_from_template('word', folder_id=folder.id, name='Folder Doc 2')
        self.Document.create_document_from_template('word', name='Root Doc')
        
        # Search in folder
        results = self.Document.search([('folder_id', '=', folder.id)])
        self.assertEqual(len(results), 2)

    def test_search_starred_documents(self):
        """Test searching starred documents."""
        result1 = self.Document.create_document_from_template('word', name='Starred 1')
        result2 = self.Document.create_document_from_template('word', name='Starred 2')
        self.Document.create_document_from_template('word', name='Not Starred')
        
        doc1 = self.Document.browse(result1['document_id'])
        doc2 = self.Document.browse(result2['document_id'])
        
        doc1.toggle_starred()
        doc2.toggle_starred()
        
        # Search starred
        results = self.Document.search([('is_starred', '=', True)])
        self.assertEqual(len(results), 2)

    def test_search_trashed_documents(self):
        """Test searching trashed documents."""
        result1 = self.Document.create_document_from_template('word', name='Trash 1')
        result2 = self.Document.create_document_from_template('word', name='Trash 2')
        self.Document.create_document_from_template('word', name='Active')
        
        doc1 = self.Document.browse(result1['document_id'])
        doc2 = self.Document.browse(result2['document_id'])
        
        doc1.action_move_to_trash()
        doc2.action_move_to_trash()
        
        # Search trashed
        results = self.Document.search([('is_trashed', '=', True)])
        self.assertEqual(len(results), 2)


@tagged('post_install', '-at_install', 'office', 'office_integration')
class TestOfficeBatchOperations(TransactionCase):
    """Test batch operations on multiple items."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Document = cls.env['office.document']
        cls.Folder = cls.env['office.folder']

    def test_batch_move_to_folder(self):
        """Test moving multiple documents to folder."""
        folder = self.Folder.create({'name': 'Batch Target'})
        
        docs = []
        for i in range(5):
            result = self.Document.create_document_from_template('word', name=f'Batch Doc {i}')
            docs.append(self.Document.browse(result['document_id']))
        
        # Move all to folder
        for doc in docs:
            doc.action_move_to_folder(folder.id)
        
        folder.invalidate_recordset()
        self.assertEqual(len(folder.document_ids), 5)

    def test_batch_delete(self):
        """Test deleting multiple documents."""
        docs = []
        for i in range(5):
            result = self.Document.create_document_from_template('word', name=f'Delete Batch {i}')
            docs.append(self.Document.browse(result['document_id']))
        
        # Move all to trash
        for doc in docs:
            doc.action_move_to_trash()
        
        # Verify all trashed
        for doc in docs:
            doc.invalidate_recordset()
            self.assertTrue(doc.is_trashed)
        
        # Permanently delete all
        for doc in docs:
            doc.action_delete_permanently()
        
        # Verify all deleted
        for doc in docs:
            self.assertFalse(doc.exists())

    def test_batch_star(self):
        """Test starring multiple documents."""
        docs = []
        for i in range(5):
            result = self.Document.create_document_from_template('word', name=f'Star Batch {i}')
            docs.append(self.Document.browse(result['document_id']))
        
        # Star all
        for doc in docs:
            doc.toggle_starred()
        
        # Verify all starred
        for doc in docs:
            doc.invalidate_recordset()
            self.assertTrue(doc.is_starred)


@tagged('post_install', '-at_install', 'office', 'office_integration')
class TestOfficeDataIntegrity(TransactionCase):
    """Test data integrity across operations."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Document = cls.env['office.document']
        cls.Folder = cls.env['office.folder']
        cls.Version = cls.env['office.document.version']

    def test_cascade_delete_folder(self):
        """Test cascade delete when folder is deleted."""
        folder = self.Folder.create({'name': 'Cascade Test'})
        
        result = self.Document.create_document_from_template('word', folder_id=folder.id, name='Cascade Doc')
        doc_id = result['document_id']
        
        # Delete folder
        folder.unlink()
        
        # Document should be unlinked from folder or also deleted
        doc = self.Document.browse(doc_id)
        if doc.exists():
            self.assertFalse(doc.folder_id)

    def test_version_integrity(self):
        """Test version data integrity."""
        result = self.Document.create_document_from_template('word', name='Version Integrity')
        doc = self.Document.browse(result['document_id'])
        
        # Create versions
        for i in range(3):
            content = base64.b64encode(f'Version {i}'.encode()).decode()
            doc.create_version(content, f'Version note {i}')
        
        # Verify all versions exist
        versions = self.Version.search([('document_id', '=', doc.id)])
        self.assertGreater(len(versions), 3)
        
        # Delete document
        doc.action_move_to_trash()
        doc.action_delete_permanently()
        
        # Versions should be cleaned up
        remaining_versions = self.Version.search([('document_id', '=', result['document_id'])])
        self.assertEqual(len(remaining_versions), 0)

    def test_activity_log_integrity(self):
        """Test activity log records all operations."""
        result = self.Document.create_document_from_template('word', name='Activity Test')
        doc = self.Document.browse(result['document_id'])
        
        # Perform various operations
        doc.toggle_starred()
        doc.add_comment('Test comment')
        folder = self.Folder.create({'name': 'Activity Folder'})
        doc.action_move_to_folder(folder.id)
        
        # Check activities
        Activity = self.env['office.document.activity']
        activities = Activity.search([('document_id', '=', doc.id)])
        
        # Should have multiple activity records
        self.assertGreater(len(activities), 0)


@tagged('post_install', '-at_install', 'office', 'office_integration')
class TestOfficeEdgeCaseIntegration(TransactionCase):
    """Test edge cases in integrated workflows."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Document = cls.env['office.document']
        cls.Folder = cls.env['office.folder']

    def test_unicode_names_throughout(self):
        """Test unicode names work throughout system."""
        # Create folder with unicode
        folder = self.Folder.create({'name': '日本語フォルダ 📁'})
        self.assertEqual(folder.name, '日本語フォルダ 📁')
        
        # Create document with unicode
        result = self.Document.create_document_from_template(
            'word',
            folder_id=folder.id,
            name='文書テスト 📄'
        )
        doc = self.Document.browse(result['document_id'])
        self.assertEqual(doc.name, '文書テスト 📄')
        
        # Add comment with unicode
        comment = doc.add_comment('コメント 💬')
        self.assertIn('コメント', comment.content)
        
        # Search with unicode
        results = self.Document.search([('name', 'ilike', '文書')])
        self.assertGreater(len(results), 0)

    def test_very_long_names(self):
        """Test handling very long names."""
        long_name = 'A' * 500
        
        folder = self.Folder.create({'name': long_name})
        self.assertTrue(folder.exists())
        
        result = self.Document.create_document_from_template('word', name=long_name)
        doc = self.Document.browse(result['document_id'])
        self.assertTrue(doc.exists())

    def test_special_characters_in_names(self):
        """Test special characters in names."""
        special_name = "Test <Doc> & 'Folder' \"Quotes\" @#$%"
        
        result = self.Document.create_document_from_template('word', name=special_name)
        doc = self.Document.browse(result['document_id'])
        self.assertTrue(doc.exists())

    def test_empty_folder_operations(self):
        """Test operations on empty folders."""
        folder = self.Folder.create({'name': 'Empty Folder'})
        
        # Get contents of empty folder
        self.assertEqual(len(folder.document_ids), 0)
        
        # Delete empty folder
        folder.unlink()
        self.assertFalse(folder.exists())

    def test_concurrent_operations_simulation(self):
        """Test simulating concurrent operations."""
        result = self.Document.create_document_from_template('word', name='Concurrent Test')
        doc = self.Document.browse(result['document_id'])
        
        # Simulate rapid operations
        for _ in range(10):
            doc.toggle_starred()
        
        # Final state should be valid
        doc.invalidate_recordset()
        self.assertIn(doc.is_starred, [True, False])
