# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ComplianceAuditLog(models.Model):
    _name = 'ringcentral.compliance.audit.log'
    _description = 'Compliance Audit Log'
    _order = 'create_date desc'
    _rec_name = 'action'

    action = fields.Char(string='Action', required=True, index=True)
    description = fields.Text(string='Description')
    details = fields.Text(string='Details', help='JSON or text details about the action')
    
    # Related records
    partner_id = fields.Many2one('res.partner', string='Data Subject', index=True)
    res_model = fields.Char(string='Model')
    res_id = fields.Integer(string='Record ID')
    
    # User info
    user_id = fields.Many2one(
        'res.users',
        string='User',
        default=lambda self: self.env.user,
    )
    
    # Additional context
    ip_address = fields.Char(string='IP Address')
    user_agent = fields.Char(string='User Agent')
    
    # Computed
    record_reference = fields.Char(
        string='Record',
        compute='_compute_record_reference',
    )

    @api.depends('res_model', 'res_id')
    def _compute_record_reference(self):
        for record in self:
            if record.res_model and record.res_id:
                try:
                    obj = self.env[record.res_model].browse(record.res_id)
                    if obj.exists():
                        record.record_reference = obj.display_name
                    else:
                        record.record_reference = f'{record.res_model},{record.res_id}'
                except Exception:
                    record.record_reference = f'{record.res_model},{record.res_id}'
            else:
                record.record_reference = ''

    @api.model
    def log_action(self, action, description, partner_id=None, res_model=None, res_id=None):
        """Utility method to create audit log entry"""
        return self.create({
            'action': action,
            'description': description,
            'partner_id': partner_id,
            'res_model': res_model,
            'res_id': res_id,
        })
