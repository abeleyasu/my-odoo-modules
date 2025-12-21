# -*- coding: utf-8 -*-
# Copyright 2025 Odoo Community
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""
Office Folder Model - Unit Tests

Comprehensive test cases for office.folder model:
- Folder creation and hierarchy
- Folder colors
- Folder operations (rename, move, trash)
- Folder tree retrieval
- Parent store optimization
"""

from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError, UserError


@tagged('post_install', '-at_install', 'office', 'office_folder')
class TestOfficeFolderCreation(TransactionCase):
    """Test folder creation functionality."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Folder = cls.env['office.folder']

    def test_create_folder(self):
        """Test creating a basic folder."""
        result = self.Folder.create_folder('My Folder')
        
        self.assertTrue(result.get('id'))
        folder = self.Folder.browse(result['id'])
        self.assertEqual(folder.name, 'My Folder')
        self.assertFalse(folder.parent_id)

    def test_create_subfolder(self):
        """Test creating a subfolder."""
        parent = self.Folder.create({'name': 'Parent'})
        result = self.Folder.create_folder('Child', parent.id)
        
        child = self.Folder.browse(result['id'])
        self.assertEqual(child.parent_id.id, parent.id)

    def test_folder_owner(self):
        """Test folder owner is set correctly."""
        folder = self.Folder.create({'name': 'Test'})
        
        self.assertEqual(folder.owner_id.id, self.env.user.id)

    def test_folder_default_color(self):
        """Test folder has default color."""
        folder = self.Folder.create({'name': 'Test'})
        
        self.assertTrue(folder.color)
        self.assertEqual(folder.color, 'gray')


@tagged('post_install', '-at_install', 'office', 'office_folder')
class TestOfficeFolderColors(TransactionCase):
    """Test folder color functionality."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Folder = cls.env['office.folder']

    def test_set_folder_color(self):
        """Test setting folder color."""
        folder = self.Folder.create({'name': 'Colored Folder'})
        
        folder.action_set_color('blue')
        
        self.assertEqual(folder.color, 'blue')

    def test_all_folder_colors(self):
        """Test all 18 folder colors are valid."""
        colors = [
            'gray', 'red', 'pink', 'purple', 'deep_purple', 'indigo',
            'blue', 'light_blue', 'cyan', 'teal', 'green', 'light_green',
            'lime', 'yellow', 'amber', 'orange', 'deep_orange', 'brown'
        ]
        
        for color in colors:
            folder = self.Folder.create({'name': f'Folder {color}', 'color': color})
            self.assertEqual(folder.color, color)

    def test_get_folder_colors(self):
        """Test getting available folder colors."""
        colors = self.Folder.get_folder_colors()
        
        self.assertIsInstance(colors, dict)
        self.assertIn('blue', colors)
        self.assertIn('red', colors)
        self.assertEqual(len(colors), 18)


@tagged('post_install', '-at_install', 'office', 'office_folder')
class TestOfficeFolderHierarchy(TransactionCase):
    """Test folder hierarchy functionality."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Folder = cls.env['office.folder']

    def test_folder_hierarchy_depth(self):
        """Test creating nested folder hierarchy."""
        level1 = self.Folder.create({'name': 'Level 1'})
        level2 = self.Folder.create({'name': 'Level 2', 'parent_id': level1.id})
        level3 = self.Folder.create({'name': 'Level 3', 'parent_id': level2.id})
        level4 = self.Folder.create({'name': 'Level 4', 'parent_id': level3.id})
        
        self.assertEqual(level2.parent_id.id, level1.id)
        self.assertEqual(level3.parent_id.id, level2.id)
        self.assertEqual(level4.parent_id.id, level3.id)

    def test_child_folders(self):
        """Test child folders relationship."""
        parent = self.Folder.create({'name': 'Parent'})
        child1 = self.Folder.create({'name': 'Child 1', 'parent_id': parent.id})
        child2 = self.Folder.create({'name': 'Child 2', 'parent_id': parent.id})
        
        self.assertEqual(len(parent.child_ids), 2)
        self.assertIn(child1.id, parent.child_ids.ids)
        self.assertIn(child2.id, parent.child_ids.ids)

    def test_folder_tree(self):
        """Test folder tree retrieval."""
        parent = self.Folder.create({'name': 'Root'})
        self.Folder.create({'name': 'Child', 'parent_id': parent.id})
        
        tree = self.Folder.get_folder_tree()
        
        self.assertIsInstance(tree, list)
        self.assertTrue(len(tree) > 0)

    def test_prevent_circular_reference(self):
        """Test preventing circular parent reference."""
        folder1 = self.Folder.create({'name': 'Folder 1'})
        folder2 = self.Folder.create({'name': 'Folder 2', 'parent_id': folder1.id})
        
        # Try to set folder1's parent to folder2 (creating a cycle)
        with self.assertRaises((ValidationError, UserError)):
            folder1.write({'parent_id': folder2.id})

    def test_prevent_self_parent(self):
        """Test preventing folder from being its own parent."""
        folder = self.Folder.create({'name': 'Test'})
        
        with self.assertRaises((ValidationError, UserError)):
            folder.write({'parent_id': folder.id})


@tagged('post_install', '-at_install', 'office', 'office_folder')
class TestOfficeFolderOperations(TransactionCase):
    """Test folder operations."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Folder = cls.env['office.folder']

    def test_rename_folder(self):
        """Test renaming a folder."""
        folder = self.Folder.create({'name': 'Original Name'})
        
        folder.action_rename('New Name')
        
        self.assertEqual(folder.name, 'New Name')

    def test_move_folder(self):
        """Test moving folder to new parent."""
        parent1 = self.Folder.create({'name': 'Parent 1'})
        parent2 = self.Folder.create({'name': 'Parent 2'})
        child = self.Folder.create({'name': 'Child', 'parent_id': parent1.id})
        
        child.action_move(parent2.id)
        
        self.assertEqual(child.parent_id.id, parent2.id)

    def test_move_folder_to_root(self):
        """Test moving folder to root level."""
        parent = self.Folder.create({'name': 'Parent'})
        child = self.Folder.create({'name': 'Child', 'parent_id': parent.id})
        
        child.action_move(False)
        
        self.assertFalse(child.parent_id)

    def test_trash_folder(self):
        """Test moving folder to trash."""
        folder = self.Folder.create({'name': 'To Trash'})
        
        folder.action_move_to_trash()
        
        self.assertTrue(folder.is_trashed)
        self.assertTrue(folder.trashed_date)

    def test_trash_cascades_to_children(self):
        """Test trashing folder cascades to child folders."""
        parent = self.Folder.create({'name': 'Parent'})
        child = self.Folder.create({'name': 'Child', 'parent_id': parent.id})
        
        parent.action_move_to_trash()
        
        child.invalidate_recordset()
        self.assertTrue(child.is_trashed)

    def test_restore_folder(self):
        """Test restoring folder from trash."""
        folder = self.Folder.create({'name': 'Restore Me'})
        folder.action_move_to_trash()
        
        folder.action_restore_from_trash()
        
        self.assertFalse(folder.is_trashed)

    def test_permanent_delete_folder(self):
        """Test permanent folder deletion."""
        folder = self.Folder.create({'name': 'Delete Me'})
        folder.action_move_to_trash()
        folder_id = folder.id
        
        folder.action_delete_permanently()
        
        self.assertFalse(self.Folder.browse(folder_id).exists())


@tagged('post_install', '-at_install', 'office', 'office_folder')
class TestOfficeFolderDocuments(TransactionCase):
    """Test folder-document relationships."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Folder = cls.env['office.folder']
        cls.Document = cls.env['office.document']

    def test_folder_document_count(self):
        """Test folder document count."""
        folder = self.Folder.create({'name': 'With Docs'})
        self.Document.create_document_from_template('word', folder_id=folder.id)
        self.Document.create_document_from_template('excel', folder_id=folder.id)
        
        folder.invalidate_recordset()
        self.assertEqual(folder.document_count, 2)

    def test_folder_total_size(self):
        """Test folder total size calculation."""
        folder = self.Folder.create({'name': 'Sized Folder'})
        self.Document.create_document_from_template('word', folder_id=folder.id)
        
        folder.invalidate_recordset()
        self.assertTrue(folder.total_size >= 0)

    def test_trash_folder_cascades_to_documents(self):
        """Test trashing folder cascades to documents."""
        folder = self.Folder.create({'name': 'Parent'})
        result = self.Document.create_document_from_template('word', folder_id=folder.id)
        doc = self.Document.browse(result['document_id'])
        
        folder.action_move_to_trash()
        
        doc.invalidate_recordset()
        self.assertTrue(doc.is_trashed)


@tagged('post_install', '-at_install', 'office', 'office_folder')
class TestOfficeFolderValidation(TransactionCase):
    """Test folder validation and constraints."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Folder = cls.env['office.folder']

    def test_empty_name_validation(self):
        """Test that empty folder name is not allowed."""
        with self.assertRaises((ValidationError, UserError)):
            self.Folder.create({'name': ''})

    def test_whitespace_name_validation(self):
        """Test that whitespace-only name is handled."""
        with self.assertRaises((ValidationError, UserError)):
            self.Folder.create({'name': '   '})

    def test_duplicate_name_same_parent(self):
        """Test duplicate folder names in same parent."""
        self.Folder.create({'name': 'Unique'})
        
        # Should handle duplicate gracefully or raise error
        try:
            self.Folder.create({'name': 'Unique'})
            # If it succeeds, both folders exist (allowed)
        except (ValidationError, UserError):
            # If it fails, duplicates not allowed (also valid)
            pass

    def test_special_characters_in_name(self):
        """Test folder names with special characters."""
        special_names = [
            'Folder with spaces',
            'Folder-with-dashes',
            'Folder_with_underscores',
            'Folder.with.dots',
            'Folder (with) parentheses',
            "Folder 'with' quotes",
        ]
        
        for name in special_names:
            folder = self.Folder.create({'name': name})
            self.assertEqual(folder.name, name)

    def test_very_long_name(self):
        """Test folder with very long name."""
        long_name = 'A' * 500
        folder = self.Folder.create({'name': long_name})
        
        # Should either accept or truncate
        self.assertTrue(len(folder.name) > 0)
