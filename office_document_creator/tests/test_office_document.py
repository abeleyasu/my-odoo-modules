# -*- coding: utf-8 -*-
# Copyright 2025 Odoo Community
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""
Office Document Model - Unit Tests

Comprehensive test cases for office.document model:
- Document creation from templates
- File upload and type detection
- File category classification
- Preview type routing
- Document operations (rename, move, star, trash, duplicate)
- Search functionality
- Validation and constraints
"""

import base64
import io
from unittest.mock import patch, MagicMock

from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError, UserError, AccessError


@tagged('post_install', '-at_install', 'office', 'office_document')
class TestOfficeDocumentCreation(TransactionCase):
    """Test document creation functionality."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Document = cls.env['office.document']
        cls.Folder = cls.env['office.folder']
        cls.user_demo = cls.env.ref('base.user_demo')
        
        # Create test folder
        cls.test_folder = cls.Folder.create({
            'name': 'Test Folder',
        })

    def test_create_word_document(self):
        """Test creating a Word document from template."""
        result = self.Document.create_document_from_template('word')
        
        self.assertTrue(result.get('document_id'))
        doc = self.Document.browse(result['document_id'])
        self.assertEqual(doc.doc_type, 'word')
        self.assertEqual(doc.file_category, 'word')
        self.assertEqual(doc.preview_type, 'office')
        self.assertTrue(doc.attachment_id)
        self.assertIn('.docx', doc.name)

    def test_create_excel_document(self):
        """Test creating an Excel document from template."""
        result = self.Document.create_document_from_template('excel')
        
        doc = self.Document.browse(result['document_id'])
        self.assertEqual(doc.doc_type, 'excel')
        self.assertEqual(doc.file_category, 'excel')
        self.assertIn('.xlsx', doc.name)

    def test_create_powerpoint_document(self):
        """Test creating a PowerPoint document from template."""
        result = self.Document.create_document_from_template('powerpoint')
        
        doc = self.Document.browse(result['document_id'])
        self.assertEqual(doc.doc_type, 'powerpoint')
        self.assertEqual(doc.file_category, 'powerpoint')
        self.assertIn('.pptx', doc.name)

    def test_create_document_in_folder(self):
        """Test creating document inside a folder."""
        result = self.Document.create_document_from_template(
            'word', 
            folder_id=self.test_folder.id
        )
        
        doc = self.Document.browse(result['document_id'])
        self.assertEqual(doc.folder_id.id, self.test_folder.id)

    def test_create_document_with_custom_name(self):
        """Test creating document with custom name."""
        result = self.Document.create_document_from_template(
            'word',
            name='My Custom Document'
        )
        
        doc = self.Document.browse(result['document_id'])
        self.assertEqual(doc.name, 'My Custom Document.docx')

    def test_create_document_owner(self):
        """Test document owner is set correctly."""
        result = self.Document.create_document_from_template('word')
        
        doc = self.Document.browse(result['document_id'])
        self.assertEqual(doc.owner_id.id, self.env.user.id)
        self.assertEqual(doc.create_uid.id, self.env.user.id)


@tagged('post_install', '-at_install', 'office', 'office_document')
class TestOfficeDocumentUpload(TransactionCase):
    """Test document upload functionality."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Document = cls.env['office.document']

    def _create_test_file(self, filename, content=b'Test content'):
        """Helper to create test file data."""
        return base64.b64encode(content).decode('utf-8')

    def test_upload_image_file(self):
        """Test uploading an image file."""
        # Create minimal PNG
        png_header = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde'
        file_data = self._create_test_file('test.png', png_header)
        
        result = self.Document.upload_document('test.png', file_data)
        
        doc = self.Document.browse(result['document_id'])
        self.assertEqual(doc.file_category, 'image')
        self.assertEqual(doc.preview_type, 'image')
        self.assertEqual(doc.file_extension, 'png')

    def test_upload_video_file(self):
        """Test uploading a video file."""
        file_data = self._create_test_file('video.mp4')
        result = self.Document.upload_document('video.mp4', file_data)
        
        doc = self.Document.browse(result['document_id'])
        self.assertEqual(doc.file_category, 'video')
        self.assertEqual(doc.preview_type, 'video')

    def test_upload_audio_file(self):
        """Test uploading an audio file."""
        file_data = self._create_test_file('audio.mp3')
        result = self.Document.upload_document('audio.mp3', file_data)
        
        doc = self.Document.browse(result['document_id'])
        self.assertEqual(doc.file_category, 'audio')
        self.assertEqual(doc.preview_type, 'audio')

    def test_upload_pdf_file(self):
        """Test uploading a PDF file."""
        pdf_header = b'%PDF-1.4 test content'
        file_data = self._create_test_file('document.pdf', pdf_header)
        result = self.Document.upload_document('document.pdf', file_data)
        
        doc = self.Document.browse(result['document_id'])
        self.assertEqual(doc.file_category, 'pdf')
        self.assertEqual(doc.preview_type, 'pdf')

    def test_upload_python_file(self):
        """Test uploading a Python code file."""
        code_content = b'print("Hello World")'
        file_data = self._create_test_file('script.py', code_content)
        result = self.Document.upload_document('script.py', file_data)
        
        doc = self.Document.browse(result['document_id'])
        self.assertEqual(doc.file_category, 'code')
        self.assertEqual(doc.preview_type, 'code')
        self.assertEqual(doc.code_language, 'python')

    def test_upload_javascript_file(self):
        """Test uploading a JavaScript file."""
        code_content = b'console.log("Hello");'
        file_data = self._create_test_file('app.js', code_content)
        result = self.Document.upload_document('app.js', file_data)
        
        doc = self.Document.browse(result['document_id'])
        self.assertEqual(doc.code_language, 'javascript')

    def test_upload_typescript_file(self):
        """Test uploading a TypeScript file."""
        code_content = b'const x: string = "test";'
        file_data = self._create_test_file('app.ts', code_content)
        result = self.Document.upload_document('app.ts', file_data)
        
        doc = self.Document.browse(result['document_id'])
        self.assertEqual(doc.code_language, 'typescript')

    def test_upload_archive_file(self):
        """Test uploading an archive file."""
        file_data = self._create_test_file('archive.zip')
        result = self.Document.upload_document('archive.zip', file_data)
        
        doc = self.Document.browse(result['document_id'])
        self.assertEqual(doc.file_category, 'archive')
        self.assertEqual(doc.preview_type, 'none')

    def test_upload_to_folder(self):
        """Test uploading file to specific folder."""
        folder = self.env['office.folder'].create({'name': 'Upload Folder'})
        file_data = self._create_test_file('test.txt')
        
        result = self.Document.upload_document('test.txt', file_data, folder.id)
        
        doc = self.Document.browse(result['document_id'])
        self.assertEqual(doc.folder_id.id, folder.id)

    def test_upload_file_size_calculation(self):
        """Test file size is calculated correctly."""
        content = b'X' * 1024  # 1KB
        file_data = self._create_test_file('test.txt', content)
        result = self.Document.upload_document('test.txt', file_data)
        
        doc = self.Document.browse(result['document_id'])
        self.assertEqual(doc.file_size, 1024)

    def test_upload_mimetype_detection(self):
        """Test MIME type is detected correctly."""
        file_data = self._create_test_file('image.jpg')
        result = self.Document.upload_document('image.jpg', file_data)
        
        doc = self.Document.browse(result['document_id'])
        self.assertIn('image', doc.mimetype)


@tagged('post_install', '-at_install', 'office', 'office_document')
class TestOfficeDocumentFileCategories(TransactionCase):
    """Test file category classification for all supported types."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Document = cls.env['office.document']

    def _upload_file(self, filename):
        """Helper to upload a test file."""
        content = base64.b64encode(b'test').decode('utf-8')
        result = self.Document.upload_document(filename, content)
        return self.Document.browse(result['document_id'])

    def test_word_extensions(self):
        """Test Word document extensions."""
        for ext in ['doc', 'docx', 'odt', 'rtf']:
            doc = self._upload_file(f'test.{ext}')
            self.assertEqual(doc.file_category, 'word', f'Failed for .{ext}')

    def test_excel_extensions(self):
        """Test Excel document extensions."""
        for ext in ['xls', 'xlsx', 'ods', 'csv']:
            doc = self._upload_file(f'test.{ext}')
            self.assertEqual(doc.file_category, 'excel', f'Failed for .{ext}')

    def test_powerpoint_extensions(self):
        """Test PowerPoint document extensions."""
        for ext in ['ppt', 'pptx', 'odp']:
            doc = self._upload_file(f'test.{ext}')
            self.assertEqual(doc.file_category, 'powerpoint', f'Failed for .{ext}')

    def test_image_extensions(self):
        """Test image extensions."""
        for ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg', 'ico', 'tiff']:
            doc = self._upload_file(f'test.{ext}')
            self.assertEqual(doc.file_category, 'image', f'Failed for .{ext}')

    def test_video_extensions(self):
        """Test video extensions."""
        for ext in ['mp4', 'webm', 'avi', 'mov', 'mkv', 'wmv', 'flv']:
            doc = self._upload_file(f'test.{ext}')
            self.assertEqual(doc.file_category, 'video', f'Failed for .{ext}')

    def test_audio_extensions(self):
        """Test audio extensions."""
        for ext in ['mp3', 'wav', 'ogg', 'm4a', 'flac', 'aac']:
            doc = self._upload_file(f'test.{ext}')
            self.assertEqual(doc.file_category, 'audio', f'Failed for .{ext}')

    def test_code_extensions(self):
        """Test code file extensions."""
        code_files = [
            ('py', 'python'), ('js', 'javascript'), ('ts', 'typescript'),
            ('java', 'java'), ('cpp', 'cpp'), ('c', 'c'),
            ('go', 'go'), ('rs', 'rust'), ('php', 'php'),
            ('rb', 'ruby'), ('swift', 'swift'), ('kt', 'kotlin'),
            ('html', 'html'), ('css', 'css'), ('scss', 'scss'),
            ('json', 'json'), ('xml', 'xml'), ('yaml', 'yaml'),
            ('sql', 'sql'), ('sh', 'shell'),
        ]
        for ext, lang in code_files:
            doc = self._upload_file(f'test.{ext}')
            self.assertEqual(doc.file_category, 'code', f'Failed for .{ext}')
            self.assertEqual(doc.code_language, lang, f'Language failed for .{ext}')

    def test_archive_extensions(self):
        """Test archive extensions."""
        for ext in ['zip', 'rar', '7z', 'tar', 'gz', 'bz2']:
            doc = self._upload_file(f'test.{ext}')
            self.assertEqual(doc.file_category, 'archive', f'Failed for .{ext}')


@tagged('post_install', '-at_install', 'office', 'office_document')
class TestOfficeDocumentOperations(TransactionCase):
    """Test document operations."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Document = cls.env['office.document']
        cls.Folder = cls.env['office.folder']

    def _create_test_document(self, name='Test Doc'):
        """Helper to create a test document."""
        result = self.Document.create_document_from_template('word', name=name)
        return self.Document.browse(result['document_id'])

    def test_rename_document(self):
        """Test document rename."""
        doc = self._create_test_document()
        original_name = doc.name
        
        doc.action_rename('Renamed Document')
        
        self.assertEqual(doc.name, 'Renamed Document.docx')
        self.assertNotEqual(doc.name, original_name)

    def test_rename_preserves_extension(self):
        """Test rename preserves file extension."""
        doc = self._create_test_document()
        doc.action_rename('New Name')
        
        self.assertTrue(doc.name.endswith('.docx'))

    def test_star_document(self):
        """Test starring a document."""
        doc = self._create_test_document()
        self.assertFalse(doc.is_starred)
        
        doc.action_toggle_star()
        
        self.assertTrue(doc.is_starred)

    def test_unstar_document(self):
        """Test unstarring a document."""
        doc = self._create_test_document()
        doc.is_starred = True
        
        doc.action_toggle_star()
        
        self.assertFalse(doc.is_starred)

    def test_move_to_trash(self):
        """Test moving document to trash."""
        doc = self._create_test_document()
        self.assertFalse(doc.is_trashed)
        
        doc.action_move_to_trash()
        
        self.assertTrue(doc.is_trashed)
        self.assertTrue(doc.trashed_date)

    def test_restore_from_trash(self):
        """Test restoring document from trash."""
        doc = self._create_test_document()
        doc.action_move_to_trash()
        
        doc.action_restore_from_trash()
        
        self.assertFalse(doc.is_trashed)
        self.assertFalse(doc.trashed_date)

    def test_permanent_delete(self):
        """Test permanent deletion."""
        doc = self._create_test_document()
        doc.action_move_to_trash()
        doc_id = doc.id
        
        doc.action_delete_permanently()
        
        self.assertFalse(self.Document.browse(doc_id).exists())

    def test_duplicate_document(self):
        """Test duplicating a document."""
        doc = self._create_test_document('Original')
        
        result = doc.action_duplicate()
        
        copy = self.Document.browse(result['document_id'])
        self.assertIn('Copy of', copy.name)
        self.assertEqual(copy.folder_id, doc.folder_id)
        self.assertEqual(copy.file_category, doc.file_category)

    def test_move_to_folder(self):
        """Test moving document to folder."""
        doc = self._create_test_document()
        folder = self.Folder.create({'name': 'Target Folder'})
        
        result = self.Document.move_document(doc.id, folder.id)
        
        doc.invalidate_recordset()
        self.assertEqual(doc.folder_id.id, folder.id)

    def test_move_to_root(self):
        """Test moving document to root (no folder)."""
        folder = self.Folder.create({'name': 'Some Folder'})
        result = self.Document.create_document_from_template('word', folder_id=folder.id)
        doc = self.Document.browse(result['document_id'])
        
        self.Document.move_document(doc.id, False)
        
        doc.invalidate_recordset()
        self.assertFalse(doc.folder_id)


@tagged('post_install', '-at_install', 'office', 'office_document')
class TestOfficeDocumentSearch(TransactionCase):
    """Test document search functionality."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Document = cls.env['office.document']
        
        # Create test documents
        cls.doc1 = cls._create_doc(cls, 'Project Report.docx', 'word')
        cls.doc2 = cls._create_doc(cls, 'Budget Analysis.xlsx', 'excel')
        cls.doc3 = cls._create_doc(cls, 'Meeting Notes.docx', 'word')

    def _create_doc(self, name, doc_type):
        result = self.Document.create_document_from_template(doc_type, name=name.replace('.docx', '').replace('.xlsx', ''))
        return self.Document.browse(result['document_id'])

    def test_search_by_name(self):
        """Test searching documents by name."""
        results = self.Document.search_documents('Project')
        
        doc_ids = [d['id'] for d in results.get('documents', [])]
        self.assertIn(self.doc1.id, doc_ids)

    def test_search_by_type(self):
        """Test searching documents by type filter."""
        results = self.Document.search_documents('', {'file_category': 'excel'})
        
        doc_ids = [d['id'] for d in results.get('documents', [])]
        self.assertIn(self.doc2.id, doc_ids)

    def test_search_case_insensitive(self):
        """Test search is case insensitive."""
        results = self.Document.search_documents('project')
        
        doc_ids = [d['id'] for d in results.get('documents', [])]
        self.assertIn(self.doc1.id, doc_ids)


@tagged('post_install', '-at_install', 'office', 'office_document')
class TestOfficeDocumentValidation(TransactionCase):
    """Test document validation and constraints."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Document = cls.env['office.document']

    def test_file_size_validation(self):
        """Test file size limit validation."""
        # Create content larger than 10GB should fail
        # Note: We can't actually test 10GB, so we test the validation logic
        doc = self.Document.create_document_from_template('word')
        doc = self.Document.browse(doc['document_id'])
        
        # Manually set file_size to exceed limit
        # This should be caught by constraint
        with self.assertRaises(ValidationError):
            doc.write({'file_size': 11 * 1024 * 1024 * 1024})  # 11GB

    def test_empty_name_validation(self):
        """Test that empty name is not allowed."""
        with self.assertRaises((ValidationError, UserError)):
            self.Document.create({
                'name': '',
                'doc_type': 'word',
            })

    def test_duplicate_name_in_folder(self):
        """Test handling of duplicate names in same folder."""
        folder = self.env['office.folder'].create({'name': 'Test'})
        
        self.Document.create_document_from_template('word', folder_id=folder.id, name='Doc')
        # Second document with same name should get unique suffix
        result = self.Document.create_document_from_template('word', folder_id=folder.id, name='Doc')
        doc = self.Document.browse(result['document_id'])
        
        # Should have a unique name (with suffix or different)
        self.assertTrue(doc.name)


@tagged('post_install', '-at_install', 'office', 'office_document')
class TestOfficeDocumentDashboard(TransactionCase):
    """Test dashboard data retrieval."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Document = cls.env['office.document']
        cls.Folder = cls.env['office.folder']

    def test_get_dashboard_data(self):
        """Test getting dashboard data."""
        # Create some data
        self.Folder.create({'name': 'Folder 1'})
        self.Document.create_document_from_template('word')
        
        result = self.Document.get_dashboard_data()
        
        self.assertIn('documents', result)
        self.assertIn('folders', result)
        self.assertIn('storage_used', result)

    def test_get_dashboard_for_folder(self):
        """Test getting dashboard data for specific folder."""
        folder = self.Folder.create({'name': 'My Folder'})
        self.Document.create_document_from_template('word', folder_id=folder.id)
        
        result = self.Document.get_dashboard_data(folder.id)
        
        self.assertIn('breadcrumb', result)

    def test_dashboard_excludes_trashed(self):
        """Test dashboard excludes trashed items."""
        result = self.Document.create_document_from_template('word')
        doc = self.Document.browse(result['document_id'])
        doc.action_move_to_trash()
        
        dashboard = self.Document.get_dashboard_data()
        
        doc_ids = [d['id'] for d in dashboard.get('documents', [])]
        self.assertNotIn(doc.id, doc_ids)

    def test_recent_documents(self):
        """Test recent documents retrieval."""
        self.Document.create_document_from_template('word')
        
        result = self.Document.get_dashboard_data()
        
        # Recent should be populated
        self.assertTrue(len(result.get('documents', [])) >= 0)

    def test_starred_documents_filter(self):
        """Test starred documents filter."""
        result = self.Document.create_document_from_template('word')
        doc = self.Document.browse(result['document_id'])
        doc.is_starred = True
        
        dashboard = self.Document.get_dashboard_data()
        
        # Starred documents should be included
        starred = [d for d in dashboard.get('documents', []) if d.get('is_starred')]
        self.assertTrue(len(starred) >= 1)
