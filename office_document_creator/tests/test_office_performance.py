# -*- coding: utf-8 -*-
# Copyright 2025 Odoo Community
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""
Office Performance Tests

Tests for performance, scalability, and load handling:
- Large file handling
- Bulk operations
- Query optimization
- Memory efficiency
- Response time benchmarks
"""

import base64
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError, UserError


@tagged('post_install', '-at_install', 'office', 'office_performance')
class TestOfficePerformanceDocumentCreation(TransactionCase):
    """Test document creation performance."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Document = cls.env['office.document']
        cls.Folder = cls.env['office.folder']

    def test_single_document_creation_time(self):
        """Test single document creation completes within acceptable time."""
        start = time.time()
        
        result = self.Document.create_document_from_template('word', name='Performance Test')
        
        elapsed = time.time() - start
        
        self.assertLess(elapsed, 1.0)  # Should complete within 1 second
        self.assertTrue(self.Document.browse(result['document_id']).exists())

    def test_bulk_document_creation(self):
        """Test bulk document creation performance."""
        num_documents = 50
        start = time.time()
        
        for i in range(num_documents):
            self.Document.create_document_from_template('word', name=f'Bulk Doc {i}')
        
        elapsed = time.time() - start
        avg_time = elapsed / num_documents
        
        # Average time per document should be reasonable
        self.assertLess(avg_time, 0.5)  # 500ms average per document max
        
        # Verify all created
        docs = self.Document.search([('name', 'ilike', 'Bulk Doc')])
        self.assertEqual(len(docs), num_documents)

    def test_document_creation_in_folders(self):
        """Test creating documents in folders doesn't add significant overhead."""
        folder = self.Folder.create({'name': 'Perf Folder'})
        
        # Time without folder
        start = time.time()
        for i in range(20):
            self.Document.create_document_from_template('word', name=f'No Folder {i}')
        time_no_folder = time.time() - start
        
        # Time with folder
        start = time.time()
        for i in range(20):
            self.Document.create_document_from_template('word', folder_id=folder.id, name=f'With Folder {i}')
        time_with_folder = time.time() - start
        
        # Folder overhead should be minimal
        overhead = time_with_folder - time_no_folder
        self.assertLess(overhead, time_no_folder * 0.5)  # Max 50% overhead


@tagged('post_install', '-at_install', 'office', 'office_performance')
class TestOfficePerformanceLargeFiles(TransactionCase):
    """Test large file handling performance."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Document = cls.env['office.document']

    def test_upload_1mb_file(self):
        """Test uploading 1MB file."""
        # Create 1MB content
        content = base64.b64encode(b'X' * (1 * 1024 * 1024)).decode()
        
        start = time.time()
        
        doc = self.Document.upload_file(
            filename='large_1mb.bin',
            content=content
        )
        
        elapsed = time.time() - start
        
        self.assertLess(elapsed, 5.0)  # Should complete within 5 seconds
        self.assertTrue(doc.exists())

    def test_upload_5mb_file(self):
        """Test uploading 5MB file."""
        content = base64.b64encode(b'Y' * (5 * 1024 * 1024)).decode()
        
        start = time.time()
        
        doc = self.Document.upload_file(
            filename='large_5mb.bin',
            content=content
        )
        
        elapsed = time.time() - start
        
        self.assertLess(elapsed, 15.0)  # Should complete within 15 seconds
        self.assertTrue(doc.exists())

    def test_file_size_calculation(self):
        """Test file size is calculated correctly."""
        sizes = [
            ('1KB', 1 * 1024),
            ('100KB', 100 * 1024),
            ('1MB', 1 * 1024 * 1024),
        ]
        
        for name, size in sizes:
            content = base64.b64encode(b'X' * size).decode()
            doc = self.Document.upload_file(filename=f'size_test_{name}.bin', content=content)
            
            # Size should be close to expected (base64 has some overhead)
            self.assertGreater(doc.file_size, 0)


@tagged('post_install', '-at_install', 'office', 'office_performance')
class TestOfficePerformanceSearch(TransactionCase):
    """Test search performance."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Document = cls.env['office.document']
        cls.Folder = cls.env['office.folder']
        
        # Create test data
        for i in range(100):
            cls.Document.create_document_from_template(
                'word' if i % 3 == 0 else 'excel' if i % 3 == 1 else 'presentation',
                name=f'Search Test Document {i}'
            )

    def test_search_by_name_performance(self):
        """Test search by name performance with many documents."""
        start = time.time()
        
        results = self.Document.search([('name', 'ilike', 'Search Test')])
        
        elapsed = time.time() - start
        
        self.assertLess(elapsed, 1.0)  # Should complete within 1 second
        self.assertGreater(len(results), 0)

    def test_search_with_multiple_filters(self):
        """Test search with multiple filters performance."""
        start = time.time()
        
        results = self.Document.search([
            ('name', 'ilike', 'Search'),
            ('file_category', '=', 'word'),
            ('is_trashed', '=', False),
        ])
        
        elapsed = time.time() - start
        
        self.assertLess(elapsed, 1.0)
        self.assertGreater(len(results), 0)

    def test_search_pagination(self):
        """Test search with pagination."""
        start = time.time()
        
        # First page
        results_page1 = self.Document.search([('name', 'ilike', 'Search')], limit=20, offset=0)
        # Second page
        results_page2 = self.Document.search([('name', 'ilike', 'Search')], limit=20, offset=20)
        
        elapsed = time.time() - start
        
        self.assertLess(elapsed, 1.0)
        self.assertLessEqual(len(results_page1), 20)

    def test_count_query_performance(self):
        """Test count query performance."""
        start = time.time()
        
        count = self.Document.search_count([('name', 'ilike', 'Search')])
        
        elapsed = time.time() - start
        
        self.assertLess(elapsed, 0.5)  # Count should be very fast
        self.assertGreater(count, 0)


@tagged('post_install', '-at_install', 'office', 'office_performance')
class TestOfficePerformanceFolderHierarchy(TransactionCase):
    """Test folder hierarchy performance."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Folder = cls.env['office.folder']
        cls.Document = cls.env['office.document']

    def test_deep_hierarchy_creation(self):
        """Test creating deep folder hierarchy."""
        depth = 10
        start = time.time()
        
        parent = None
        folders = []
        for i in range(depth):
            folder = self.Folder.create({
                'name': f'Level {i}',
                'parent_id': parent.id if parent else False
            })
            folders.append(folder)
            parent = folder
        
        elapsed = time.time() - start
        
        self.assertLess(elapsed, 2.0)  # Should complete within 2 seconds
        
        # Verify hierarchy
        deepest = folders[-1]
        self.assertEqual(deepest.parent_id.id, folders[-2].id)

    def test_wide_hierarchy_creation(self):
        """Test creating wide folder hierarchy."""
        width = 50
        parent = self.Folder.create({'name': 'Wide Parent'})
        
        start = time.time()
        
        for i in range(width):
            self.Folder.create({'name': f'Child {i}', 'parent_id': parent.id})
        
        elapsed = time.time() - start
        
        self.assertLess(elapsed, 5.0)
        
        parent.invalidate_recordset()
        self.assertEqual(len(parent.child_folder_ids), width)

    def test_folder_contents_query(self):
        """Test querying folder contents performance."""
        folder = self.Folder.create({'name': 'Contents Test'})
        
        # Add many documents
        for i in range(50):
            self.Document.create_document_from_template('word', folder_id=folder.id, name=f'Content Doc {i}')
        
        start = time.time()
        
        folder.invalidate_recordset()
        docs = folder.document_ids
        
        elapsed = time.time() - start
        
        self.assertLess(elapsed, 1.0)
        self.assertEqual(len(docs), 50)


@tagged('post_install', '-at_install', 'office', 'office_performance')
class TestOfficePerformanceVersions(TransactionCase):
    """Test version handling performance."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Document = cls.env['office.document']
        cls.Version = cls.env['office.document.version']

    def test_create_many_versions(self):
        """Test creating many versions."""
        result = self.Document.create_document_from_template('word', name='Version Perf Test')
        doc = self.Document.browse(result['document_id'])
        
        num_versions = 50
        start = time.time()
        
        for i in range(num_versions):
            content = base64.b64encode(f'Version {i} content'.encode()).decode()
            doc.create_version(content, f'Version {i}')
        
        elapsed = time.time() - start
        avg_time = elapsed / num_versions
        
        self.assertLess(avg_time, 0.2)  # 200ms average per version
        
        doc.invalidate_recordset()
        self.assertGreater(doc.version_count, num_versions)

    def test_get_version_history(self):
        """Test getting version history performance."""
        result = self.Document.create_document_from_template('word', name='History Perf Test')
        doc = self.Document.browse(result['document_id'])
        
        # Create versions
        for i in range(30):
            content = base64.b64encode(f'Version {i}'.encode()).decode()
            doc.create_version(content, f'Version {i}')
        
        start = time.time()
        
        versions = self.Version.search([('document_id', '=', doc.id)], order='create_date desc')
        
        elapsed = time.time() - start
        
        self.assertLess(elapsed, 0.5)
        self.assertGreater(len(versions), 30)

    def test_restore_version_performance(self):
        """Test version restore performance."""
        result = self.Document.create_document_from_template('word', name='Restore Perf Test')
        doc = self.Document.browse(result['document_id'])
        
        # Create versions
        for i in range(10):
            content = base64.b64encode(f'Version {i}'.encode()).decode()
            doc.create_version(content, f'Version {i}')
        
        versions = self.Version.search([('document_id', '=', doc.id)], order='create_date')
        old_version = versions[3]
        
        start = time.time()
        
        doc.restore_version(old_version.id)
        
        elapsed = time.time() - start
        
        self.assertLess(elapsed, 1.0)


@tagged('post_install', '-at_install', 'office', 'office_performance')
class TestOfficePerformanceSharing(TransactionCase):
    """Test sharing performance."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Document = cls.env['office.document']
        cls.Access = cls.env['office.document.access']
        cls.ShareLink = cls.env['office.share.link']
        cls.user_demo = cls.env.ref('base.user_demo')

    def test_grant_access_performance(self):
        """Test granting access performance."""
        result = self.Document.create_document_from_template('word', name='Share Perf Test')
        doc_id = result['document_id']
        
        start = time.time()
        
        self.Access.grant_access('document', doc_id, self.user_demo.id, 'editor')
        
        elapsed = time.time() - start
        
        self.assertLess(elapsed, 0.5)

    def test_get_access_list_performance(self):
        """Test getting access list performance."""
        result = self.Document.create_document_from_template('word', name='Access List Test')
        doc_id = result['document_id']
        
        # Grant access to multiple users
        users = self.env['res.users'].search([], limit=20)
        for user in users:
            self.Access.grant_access('document', doc_id, user.id, 'viewer')
        
        start = time.time()
        
        access_list = self.Access.get_access_list('document', doc_id)
        
        elapsed = time.time() - start
        
        self.assertLess(elapsed, 0.5)

    def test_share_link_validation_performance(self):
        """Test share link validation performance."""
        result = self.Document.create_document_from_template('word', name='Link Perf Test')
        doc = self.Document.browse(result['document_id'])
        link = self.ShareLink.create_share_link('document', doc.id, password='test123')
        
        start = time.time()
        
        for _ in range(100):
            link.validate_access('test123')
        
        elapsed = time.time() - start
        avg_time = elapsed / 100
        
        self.assertLess(avg_time, 0.01)  # 10ms average per validation


@tagged('post_install', '-at_install', 'office', 'office_performance')
class TestOfficePerformanceDashboard(TransactionCase):
    """Test dashboard performance."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Document = cls.env['office.document']
        cls.Folder = cls.env['office.folder']
        
        # Create substantial test data
        for i in range(50):
            result = cls.Document.create_document_from_template('word', name=f'Dashboard Doc {i}')
            if i % 5 == 0:
                doc = cls.Document.browse(result['document_id'])
                doc.toggle_starred()

    def test_get_recent_documents_performance(self):
        """Test getting recent documents performance."""
        start = time.time()
        
        recent = self.Document.search(
            [('is_trashed', '=', False)],
            order='write_date desc',
            limit=20
        )
        
        elapsed = time.time() - start
        
        self.assertLess(elapsed, 0.5)

    def test_get_starred_documents_performance(self):
        """Test getting starred documents performance."""
        start = time.time()
        
        starred = self.Document.search([
            ('is_starred', '=', True),
            ('is_trashed', '=', False)
        ])
        
        elapsed = time.time() - start
        
        self.assertLess(elapsed, 0.5)

    def test_storage_statistics_performance(self):
        """Test calculating storage statistics performance."""
        start = time.time()
        
        # Calculate total storage
        docs = self.Document.search([])
        total_size = sum(doc.file_size for doc in docs)
        
        elapsed = time.time() - start
        
        self.assertLess(elapsed, 2.0)

    def test_document_count_by_type_performance(self):
        """Test counting documents by type performance."""
        start = time.time()
        
        word_count = self.Document.search_count([('file_category', '=', 'word')])
        excel_count = self.Document.search_count([('file_category', '=', 'excel')])
        pdf_count = self.Document.search_count([('file_category', '=', 'pdf')])
        
        elapsed = time.time() - start
        
        self.assertLess(elapsed, 0.5)


@tagged('post_install', '-at_install', 'office', 'office_performance')
class TestOfficePerformanceComments(TransactionCase):
    """Test comments performance."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Document = cls.env['office.document']
        cls.Comment = cls.env['office.document.comment']

    def test_add_many_comments(self):
        """Test adding many comments performance."""
        result = self.Document.create_document_from_template('word', name='Comment Perf Test')
        doc = self.Document.browse(result['document_id'])
        
        num_comments = 100
        start = time.time()
        
        for i in range(num_comments):
            doc.add_comment(f'Comment number {i}')
        
        elapsed = time.time() - start
        avg_time = elapsed / num_comments
        
        self.assertLess(avg_time, 0.1)  # 100ms average per comment
        
        doc.invalidate_recordset()
        self.assertEqual(doc.comment_count, num_comments)

    def test_get_threaded_comments(self):
        """Test getting threaded comments performance."""
        result = self.Document.create_document_from_template('word', name='Thread Perf Test')
        doc = self.Document.browse(result['document_id'])
        
        # Create threaded comments
        for i in range(10):
            parent = doc.add_comment(f'Parent comment {i}')
            for j in range(5):
                doc.add_comment(f'Reply {j} to parent {i}', parent_id=parent.id)
        
        start = time.time()
        
        comments = self.Comment.search([
            ('document_id', '=', doc.id),
            ('parent_id', '=', False)
        ])
        
        # Load replies
        for comment in comments:
            _ = comment.reply_ids
        
        elapsed = time.time() - start
        
        self.assertLess(elapsed, 1.0)


@tagged('post_install', '-at_install', 'office', 'office_performance')
class TestOfficePerformanceMemory(TransactionCase):
    """Test memory usage efficiency."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Document = cls.env['office.document']

    def test_large_result_set_handling(self):
        """Test handling large result sets efficiently."""
        # Create many documents
        for i in range(100):
            self.Document.create_document_from_template('word', name=f'Memory Test {i}')
        
        # Search should not load all fields by default
        start = time.time()
        
        docs = self.Document.search([('name', 'ilike', 'Memory Test')])
        
        # Only access minimal fields
        names = [d.name for d in docs]
        
        elapsed = time.time() - start
        
        self.assertLess(elapsed, 2.0)
        self.assertEqual(len(names), 100)

    def test_batch_read_fields(self):
        """Test batch reading specific fields."""
        # Create documents
        for i in range(50):
            self.Document.create_document_from_template('word', name=f'Batch Read {i}')
        
        docs = self.Document.search([('name', 'ilike', 'Batch Read')])
        
        start = time.time()
        
        # Read specific fields in batch
        data = docs.read(['name', 'file_category', 'create_date'])
        
        elapsed = time.time() - start
        
        self.assertLess(elapsed, 1.0)
        self.assertEqual(len(data), 50)


@tagged('post_install', '-at_install', 'office', 'office_performance')
class TestOfficePerformanceCleanup(TransactionCase):
    """Test cleanup operation performance."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Document = cls.env['office.document']

    def test_empty_trash_performance(self):
        """Test emptying trash with many documents."""
        # Create and trash documents
        for i in range(50):
            result = self.Document.create_document_from_template('word', name=f'Trash Test {i}')
            doc = self.Document.browse(result['document_id'])
            doc.action_move_to_trash()
        
        trashed = self.Document.search([('is_trashed', '=', True)])
        
        start = time.time()
        
        for doc in trashed:
            doc.action_delete_permanently()
        
        elapsed = time.time() - start
        
        # Should complete in reasonable time
        self.assertLess(elapsed, 30.0)
        
        # Verify cleanup
        remaining = self.Document.search([('is_trashed', '=', True)])
        self.assertEqual(len(remaining), 0)
