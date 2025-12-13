# -*- coding: utf-8 -*-
import base64
import logging
import os
from odoo import http, _
from odoo.http import request

_logger = logging.getLogger(__name__)

TEMPLATE_MAP = {
    'word': ('blank.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
    'excel': ('blank.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
    'powerpoint': ('blank.pptx', 'application/vnd.openxmlformats-officedocument.presentationml.presentation'),
}

class OfficeController(http.Controller):

    @http.route('/office/create/<string:doc_type>', type='http', auth='user', methods=['GET'])
    def create_document(self, doc_type, **kwargs):
        """Create a new blank document"""
        if doc_type not in TEMPLATE_MAP:
            return request.render('http_routing.404')
        
        template_file, mimetype = TEMPLATE_MAP[doc_type]
        
        # Get template file path
        module_path = os.path.dirname(os.path.dirname(__file__))
        template_path = os.path.join(module_path, 'static', 'templates', template_file)
        
        if not os.path.exists(template_path):
            _logger.error(f'Template file not found: {template_path}')
            return request.render('http_routing.404')
        
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
        
        while request.env['office.document'].search([('name', '=', name), ('owner_id', '=', request.env.user.id)], limit=1):
            name = f'{base_name} {count}'
            count += 1
        
        # Create attachment
        attachment = request.env['ir.attachment'].create({
            'name': name,
            'datas': base64.b64encode(file_data),
            'mimetype': mimetype,
            'res_model': 'office.document',
        })
        
        # Create document
        document = request.env['office.document'].create({
            'name': name,
            'document_type': doc_type,
            'attachment_id': attachment.id,
            'owner_id': request.env.user.id,
        })
        
        # Link attachment to document
        attachment.res_id = document.id
        
        _logger.info(f'Created new {doc_type} document: {name} (ID: {document.id})')
        
        # Redirect to document list with notification
        return request.redirect(f'/web#action=office_document_creator.action_office_document&active_id={document.id}')
    
    @http.route('/office/quick_create', type='json', auth='user', methods=['POST'])
    def quick_create_document(self, doc_type, **kwargs):
        """JSON endpoint for quick create (used by buttons)"""
        if doc_type not in TEMPLATE_MAP:
            return {'error': 'Invalid document type'}
        
        template_file, mimetype = TEMPLATE_MAP[doc_type]
        
        # Get template file path
        module_path = os.path.dirname(os.path.dirname(__file__))
        template_path = os.path.join(module_path, 'static', 'templates', template_file)
        
        if not os.path.exists(template_path):
            return {'error': 'Template not found'}
        
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
        
        while request.env['office.document'].search([('name', '=', name), ('owner_id', '=', request.env.user.id)], limit=1):
            name = f'{base_name} {count}'
            count += 1
        
        # Create attachment
        attachment = request.env['ir.attachment'].create({
            'name': name,
            'datas': base64.b64encode(file_data),
            'mimetype': mimetype,
            'res_model': 'office.document',
        })
        
        # Create document
        document = request.env['office.document'].create({
            'name': name,
            'document_type': doc_type,
            'attachment_id': attachment.id,
            'owner_id': request.env.user.id,
        })
        
        # Link attachment to document
        attachment.res_id = document.id
        
        return {
            'document_id': document.id,
            'name': name,
            'attachment_id': attachment.id,
        }
