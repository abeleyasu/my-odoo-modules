# -*- coding: utf-8 -*-
"""
Extend hr.department with RingCentral multi-line configuration.

Adds:
- Link to department's call queue
- Department-specific phone number
- Auto-routing for inbound calls
"""

from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class HrDepartment(models.Model):
    """Extend HR departments with RingCentral call queue integration."""
    
    _inherit = 'hr.department'
    
    # ===========================
    # Call Queue Integration
    # ===========================
    
    ringcentral_call_queue_id = fields.Many2one(
        'ringcentral.call.queue',
        string='RingCentral Call Queue',
        ondelete='set null',
        domain="[('company_id', '=', company_id)]",
        help='Call queue for routing calls to this department'
    )
    
    ringcentral_queue_name = fields.Char(
        related='ringcentral_call_queue_id.name',
        string='Queue Name',
        readonly=True,
    )
    
    ringcentral_queue_extension = fields.Char(
        related='ringcentral_call_queue_id.extension_number',
        string='Queue Extension',
        readonly=True,
    )
    
    # ===========================
    # Department Phone Number
    # ===========================
    
    ringcentral_phone_number_id = fields.Many2one(
        'ringcentral.phone.number',
        string='Department Phone Number',
        ondelete='set null',
        domain="[('can_be_caller_id', '=', True), ('company_id', '=', company_id)]",
        help='Primary phone number for this department'
    )
    
    ringcentral_phone = fields.Char(
        related='ringcentral_phone_number_id.phone_number',
        string='Phone',
        readonly=True,
    )
    
    ringcentral_formatted_phone = fields.Char(
        related='ringcentral_phone_number_id.formatted_number',
        string='Formatted Phone',
        readonly=True,
    )
    
    # ===========================
    # Routing Configuration
    # ===========================
    
    ringcentral_routing_enabled = fields.Boolean(
        string='Enable RC Routing',
        default=True,
        help='Enable RingCentral call routing for this department'
    )
    
    ringcentral_use_queue_for_outbound = fields.Boolean(
        string='Use Queue for Outbound',
        default=False,
        help='Department members use queue number for outbound calls'
    )
    
    # ===========================
    # Statistics
    # ===========================
    
    ringcentral_member_count = fields.Integer(
        related='ringcentral_call_queue_id.member_count',
        string='Queue Members',
        readonly=True,
    )
    
    ringcentral_active_extension_count = fields.Integer(
        string='Active Extensions',
        compute='_compute_active_extensions',
        help='Number of department employees with active RingCentral extensions'
    )
    
    # ===========================
    # Computed Methods
    # ===========================
    
    @api.depends('member_ids', 'member_ids.user_id', 'member_ids.user_id.rc_multiline_ext_id')
    def _compute_active_extensions(self):
        for dept in self:
            count = 0
            for employee in dept.member_ids:
                if employee.user_id and employee.user_id.rc_multiline_ext_id:
                    if employee.user_id.rc_multiline_ext_id.status == 'Enabled':
                        count += 1
            dept.ringcentral_active_extension_count = count
    
    # ===========================
    # Business Methods
    # ===========================
    
    def get_department_caller_id(self):
        """
        Get the caller ID for this department.
        
        Priority:
        1. Department's specific phone number
        2. Call queue's primary number
        3. None (use company default)
        
        :return: phone_number string or False
        """
        self.ensure_one()
        
        if self.ringcentral_phone_number_id:
            return self.ringcentral_phone_number_id.phone_number
        
        if self.ringcentral_call_queue_id and self.ringcentral_call_queue_id.phone_number_id:
            return self.ringcentral_call_queue_id.phone_number_id.phone_number
        
        return False
    
    def get_department_members_extensions(self):
        """
        Get all RingCentral extensions for department members.
        
        :return: ringcentral.extension recordset
        """
        self.ensure_one()
        
        Extension = self.env['ringcentral.extension']
        extension_ids = []
        
        for employee in self.member_ids:
            if employee.user_id and employee.user_id.rc_multiline_ext_id:
                extension_ids.append(employee.user_id.rc_multiline_ext_id.id)
        
        return Extension.browse(extension_ids)
    
    def action_link_call_queue(self):
        """Open wizard to link this department to a call queue."""
        self.ensure_one()
        
        # Try auto-match by name
        CallQueue = self.env['ringcentral.call.queue']
        matching = CallQueue.search([
            ('name', 'ilike', self.name),
            ('company_id', '=', self.company_id.id),
            ('department_id', '=', False),
        ], limit=1)
        
        if matching:
            self.ringcentral_call_queue_id = matching
            matching.department_id = self
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Call Queue Linked'),
                    'message': _('Automatically linked to call queue: %s') % matching.name,
                    'type': 'success',
                    'sticky': False,
                }
            }
        
        # Open selection view
        return {
            'type': 'ir.actions.act_window',
            'name': _('Select Call Queue'),
            'res_model': 'ringcentral.call.queue',
            'view_mode': 'tree,form',
            'domain': [
                ('company_id', '=', self.company_id.id),
                ('department_id', '=', False),
            ],
            'context': {
                'link_to_department_id': self.id,
            },
            'target': 'new',
        }
    
    def action_view_queue_members(self):
        """View all members in the linked call queue."""
        self.ensure_one()
        
        if not self.ringcentral_call_queue_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Queue'),
                    'message': _('No call queue linked to this department.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        return self.ringcentral_call_queue_id.action_view_members()
    
    def action_sync_queue(self):
        """Sync the linked call queue data from RingCentral."""
        self.ensure_one()
        
        if not self.ringcentral_call_queue_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Queue'),
                    'message': _('No call queue linked to this department.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        # Trigger sync
        SyncService = self.env['ringcentral.sync.service']
        SyncService.sync_queue_members(self.ringcentral_call_queue_id)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Sync Complete'),
                'message': _('Queue members synchronized.'),
                'type': 'success',
                'sticky': False,
            }
        }
    
    # ===========================
    # Auto-linking Methods
    # ===========================
    
    @api.model
    def auto_link_queues_by_name(self, company=None):
        """
        Auto-link departments to call queues based on name matching.
        
        :param company: res.company record (defaults to current company)
        :return: Dict with results
        """
        company = company or self.env.company
        
        results = {
            'linked': 0,
            'already_linked': 0,
            'no_match': 0,
        }
        
        departments = self.search([
            ('company_id', '=', company.id),
            ('ringcentral_call_queue_id', '=', False),
        ])
        
        CallQueue = self.env['ringcentral.call.queue']
        
        for dept in departments:
            if dept.ringcentral_call_queue_id:
                results['already_linked'] += 1
                continue
            
            # Try exact match first, then fuzzy
            matching = CallQueue.search([
                ('name', '=ilike', dept.name),
                ('company_id', '=', company.id),
                ('department_id', '=', False),
            ], limit=1)
            
            if not matching:
                # Try partial match
                matching = CallQueue.search([
                    ('name', 'ilike', dept.name),
                    ('company_id', '=', company.id),
                    ('department_id', '=', False),
                ], limit=1)
            
            if matching:
                dept.ringcentral_call_queue_id = matching
                matching.department_id = dept
                results['linked'] += 1
                _logger.info(f"Auto-linked department {dept.name} to queue {matching.name}")
            else:
                results['no_match'] += 1
        
        return results
