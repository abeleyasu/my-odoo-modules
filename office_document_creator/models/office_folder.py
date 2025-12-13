# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class OfficeFolder(models.Model):
    _name = 'office.folder'
    _description = 'Office Folder'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _parent_name = 'parent_id'
    _order = 'name'

    name = fields.Char(
        string='Folder Name',
        required=True,
        tracking=True,
        index=True,
    )
    parent_id = fields.Many2one(
        'office.folder',
        string='Parent Folder',
        ondelete='cascade',
        index=True,
    )
    child_ids = fields.One2many(
        'office.folder',
        'parent_id',
        string='Sub Folders',
    )
    document_ids = fields.One2many(
        'office.document',
        'folder_id',
        string='Documents',
        domain=[('is_trashed', '=', False)],
    )
    owner_id = fields.Many2one(
        'res.users',
        string='Owner',
        default=lambda self: self.env.user,
        required=True,
        index=True,
    )
    document_count = fields.Integer(
        string='Document Count',
        compute='_compute_document_count',
    )
    color = fields.Integer(
        string='Color Index',
        default=0,
    )
    is_starred = fields.Boolean(
        string='Starred',
        default=False,
    )
    description = fields.Text(
        string='Description',
    )
    shared_user_ids = fields.Many2many(
        'res.users',
        'office_folder_share_rel',
        'folder_id',
        'user_id',
        string='Shared With',
    )

    @api.depends('document_ids')
    def _compute_document_count(self):
        for record in self:
            record.document_count = self.env['office.document'].search_count([
                ('folder_id', '=', record.id),
                ('is_trashed', '=', False),
            ])

    @api.constrains('parent_id')
    def _check_parent_recursion(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive folders.'))

    def action_open_folder(self):
        """Open folder and show its documents"""
        self.ensure_one()
        return {
            'name': self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'office.document',
            'view_mode': 'kanban,list,form',
            'domain': [('folder_id', '=', self.id), ('is_trashed', '=', False)],
            'context': {'default_folder_id': self.id},
        }

    def action_toggle_star(self):
        """Toggle starred status"""
        self.ensure_one()
        self.is_starred = not self.is_starred

    # RPC helpers for dashboard
    @api.model
    def create_folder(self, name, parent_id=False):
        name = (name or '').strip()
        if not name:
            raise ValidationError(_('Folder name cannot be empty.'))
        
        # Ensure parent_id is an integer or False
        # Handle case where parent_id might be passed as dict, None, or other types
        if parent_id:
            if isinstance(parent_id, dict):
                parent_id = parent_id.get('id', False) if parent_id else False
            elif isinstance(parent_id, (list, tuple)):
                parent_id = parent_id[0] if parent_id else False
            try:
                parent_id = int(parent_id) if parent_id else False
            except (ValueError, TypeError):
                parent_id = False
        else:
            parent_id = False
            
        domain = [('name', '=', name), ('owner_id', '=', self.env.user.id)]
        if parent_id:
            domain.append(('parent_id', '=', parent_id))
        else:
            domain.append(('parent_id', '=', False))
        existing = self.search(domain, limit=1)
        if existing:
            raise ValidationError(_('A folder with this name already exists here.'))
        folder = self.create({
            'name': name,
            'parent_id': parent_id or False,
            'owner_id': self.env.user.id,
        })
        return folder.read(['id', 'name', 'parent_id'])[0]

    @api.model
    def get_folder_tree(self, parent_id=False):
        """Get folder tree structure for navigation"""
        domain = [('owner_id', '=', self.env.user.id), ('parent_id', '=', parent_id)]
        folders = self.search(domain, order='name')
        result = []
        for folder in folders:
            result.append({
                'id': folder.id,
                'name': folder.name,
                'document_count': folder.document_count,
                'children': self.get_folder_tree(folder.id),
                'is_starred': folder.is_starred,
            })
        return result

    @api.model
    def get_folder_path(self, folder_id):
        """Get breadcrumb path from root to folder."""
        # Handle dict/list parameters from XML-RPC
        if folder_id:
            if isinstance(folder_id, dict):
                folder_id = folder_id.get('id', False)
            elif isinstance(folder_id, (list, tuple)):
                folder_id = folder_id[0] if folder_id else False
            try:
                folder_id = int(folder_id) if folder_id else False
            except (ValueError, TypeError):
                return []
        
        if not folder_id:
            return []
            
        path = []
        folder = self.browse(folder_id).exists()
        while folder:
            path.insert(0, {'id': folder.id, 'name': folder.name})
            folder = folder.parent_id
        return path
