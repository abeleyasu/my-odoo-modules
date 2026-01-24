# -*- coding: utf-8 -*-
"""
RingCentral Call Queue Model
============================

Represents Call Queues (Department-type extensions) synced from RingCentral.
Call Queues enable department-based routing with multiple members.

Industry Standard Implementation:
- Synced from RingCentral API /restapi/v1.0/account/~/call-queues
- Supports routing types: Rotating, Simultaneous, Sequential
- Links to HR departments for organizational mapping
- Tracks queue members and their availability
"""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging
import json

_logger = logging.getLogger(__name__)


class RingCentralCallQueue(models.Model):
    """RingCentral Call Queue for department-based call routing."""
    
    _name = 'ringcentral.call.queue'
    _description = 'RingCentral Call Queue'
    _order = 'name'
    _rec_name = 'name'
    
    # ===========================
    # Core Fields
    # ===========================
    
    name = fields.Char(
        string='Queue Name',
        required=True,
        index=True,
        help='Name of the call queue'
    )
    
    rc_queue_id = fields.Char(
        string='RC Queue ID',
        required=True,
        index=True,
        help='RingCentral call queue extension ID'
    )
    
    extension_number = fields.Char(
        string='Extension Number',
        help='Internal dial code for this queue'
    )
    
    status = fields.Selection([
        ('Enabled', 'Enabled'),
        ('Disabled', 'Disabled'),
        ('NotActivated', 'Not Activated'),
        ('Frozen', 'Frozen'),
    ], string='Status',
       default='Enabled')
    
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Active queues are usable for routing'
    )
    
    # ===========================
    # Queue Configuration
    # ===========================
    
    routing_type = fields.Selection([
        ('Rotating', 'Rotating'),
        ('Simultaneous', 'Simultaneous'),
        ('Sequential', 'Sequential'),
        ('FixedOrder', 'Fixed Order'),
    ], string='Routing Type',
       default='Rotating',
       help='''
       - Rotating: Distribute calls evenly among members
       - Simultaneous: Ring all members at once
       - Sequential: Ring members in sequence
       - Fixed Order: Always ring in the same order
       ''')
    
    max_wait_time = fields.Integer(
        string='Max Wait Time (sec)',
        default=300,
        help='Maximum time caller waits before overflow action'
    )
    
    wrap_up_time = fields.Integer(
        string='Wrap-Up Time (sec)',
        default=15,
        help='Time between calls for members'
    )
    
    ring_time = fields.Integer(
        string='Ring Time per Member (sec)',
        default=20,
        help='How long to ring each member before moving to next'
    )
    
    # ===========================
    # Overflow Settings
    # ===========================
    
    overflow_action = fields.Selection([
        ('Voicemail', 'Send to Voicemail'),
        ('Extension', 'Forward to Extension'),
        ('ExternalNumber', 'Forward to External Number'),
        ('Disconnect', 'Disconnect'),
        ('PlayAnnouncement', 'Play Announcement'),
    ], string='Overflow Action',
       default='Voicemail',
       help='What to do when queue times out')
    
    overflow_extension_id = fields.Many2one(
        'ringcentral.extension',
        string='Overflow Extension',
        ondelete='set null',
        help='Extension to transfer to on overflow'
    )
    
    overflow_external_number = fields.Char(
        string='Overflow External Number',
        help='External number to transfer to on overflow'
    )
    
    # ===========================
    # Relationships
    # ===========================
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        ondelete='cascade',
    )
    
    extension_id = fields.Many2one(
        'ringcentral.extension',
        string='Queue Extension',
        ondelete='cascade',
        help='The Department-type extension for this queue'
    )
    
    department_id = fields.Many2one(
        'hr.department',
        string='HR Department',
        ondelete='set null',
        help='Link to Odoo HR department'
    )
    
    phone_number_id = fields.Many2one(
        'ringcentral.phone.number',
        string='Primary Phone Number',
        ondelete='set null',
        help='Primary DID for this call queue'
    )
    
    phone_number_ids = fields.One2many(
        'ringcentral.phone.number',
        'call_queue_id',
        string='Phone Numbers',
        help='All phone numbers assigned to this queue'
    )
    
    # ===========================
    # Queue Members
    # ===========================
    
    member_ids = fields.Many2many(
        'ringcentral.extension',
        'ringcentral_queue_member_rel',
        'queue_id',
        'extension_id',
        string='Queue Members',
        help='Extensions that are members of this queue'
    )
    
    member_count = fields.Integer(
        string='Member Count',
        compute='_compute_member_count',
        store=True,
    )
    
    # ===========================
    # Statistics
    # ===========================
    
    total_calls_today = fields.Integer(
        string='Calls Today',
        compute='_compute_stats',
        help='Number of calls received today'
    )
    
    avg_wait_time_today = fields.Float(
        string='Avg Wait Time (sec)',
        compute='_compute_stats',
        help='Average wait time today'
    )
    
    # ===========================
    # Sync Tracking
    # ===========================
    
    last_sync_date = fields.Datetime(
        string='Last Synced',
        help='Last time this queue was synced from RingCentral'
    )
    
    rc_data_json = fields.Text(
        string='Raw RC Data',
        help='Full JSON response from RingCentral for debugging'
    )
    
    # ===========================
    # Computed Methods
    # ===========================
    
    @api.depends('member_ids')
    def _compute_member_count(self):
        for queue in self:
            queue.member_count = len(queue.member_ids)
    
    def _compute_stats(self):
        """Compute queue statistics - placeholder for actual implementation."""
        # TODO: Integrate with call log data when available
        for queue in self:
            queue.total_calls_today = 0
            queue.avg_wait_time_today = 0.0
    
    # ===========================
    # Constraints
    # ===========================
    
    _sql_constraints = [
        ('rc_queue_company_unique',
         'UNIQUE(rc_queue_id, company_id)',
         'RingCentral Queue ID must be unique per company.'),
    ]
    
    # ===========================
    # Business Methods
    # ===========================
    
    def sync_from_ringcentral(self, queue_data):
        """
        Update queue from RingCentral API response.
        
        :param queue_data: Dict from RingCentral call queue API
        """
        self.ensure_one()
        
        vals = {
            'name': queue_data.get('name', self.name),
            'extension_number': queue_data.get('extensionNumber'),
            'status': queue_data.get('status', 'Enabled'),
            'last_sync_date': fields.Datetime.now(),
            'rc_data_json': json.dumps(queue_data),
        }
        
        # Parse queue settings if present
        settings = queue_data.get('settings', {})
        if settings:
            routing = settings.get('callHandlingAction', 'Rotating')
            vals['routing_type'] = routing if routing in dict(self._fields['routing_type'].selection) else 'Rotating'
            vals['max_wait_time'] = settings.get('maxWaitTime', 300)
            vals['wrap_up_time'] = settings.get('wrapUpTime', 15)
        
        self.write(vals)
        _logger.info(f"Synced call queue: {self.name}")
    
    @api.model
    def create_or_update_from_api(self, queue_data, company):
        """
        Create or update a call queue from RingCentral API data.
        
        :param queue_data: Dict from RingCentral API
        :param company: res.company record
        :return: ringcentral.call.queue record
        """
        rc_queue_id = str(queue_data.get('id'))
        
        existing = self.search([
            ('rc_queue_id', '=', rc_queue_id),
            ('company_id', '=', company.id),
        ], limit=1)
        
        if existing:
            existing.sync_from_ringcentral(queue_data)
            return existing
        
        # Create new queue
        vals = {
            'name': queue_data.get('name', f'Queue {rc_queue_id}'),
            'rc_queue_id': rc_queue_id,
            'extension_number': queue_data.get('extensionNumber'),
            'status': queue_data.get('status', 'Enabled'),
            'company_id': company.id,
            'last_sync_date': fields.Datetime.now(),
            'rc_data_json': json.dumps(queue_data),
        }
        
        new_queue = self.create(vals)
        _logger.info(f"Created call queue: {new_queue.name}")
        return new_queue
    
    def action_sync_members(self):
        """Sync queue members from RingCentral."""
        self.ensure_one()
        # This will be implemented by the sync service
        return self.env['ringcentral.sync.service'].sync_queue_members(self)
    
    def action_link_to_department(self):
        """Open wizard to link this queue to an HR department."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Link to Department'),
            'res_model': 'hr.department',
            'view_mode': 'tree,form',
            'target': 'current',
            'context': {
                'default_ringcentral_call_queue_id': self.id,
            }
        }
    
    def action_view_members(self):
        """View all members of this queue."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Queue Members'),
            'res_model': 'ringcentral.extension',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.member_ids.ids)],
        }
    
    def action_view_phone_numbers(self):
        """View phone numbers assigned to this queue."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Queue Phone Numbers'),
            'res_model': 'ringcentral.phone.number',
            'view_mode': 'tree,form',
            'domain': [('call_queue_id', '=', self.id)],
        }


class RingCentralPhoneNumber(models.Model):
    """Add call_queue_id to phone numbers."""
    _inherit = 'ringcentral.phone.number'
    
    call_queue_id = fields.Many2one(
        'ringcentral.call.queue',
        string='Call Queue',
        ondelete='set null',
        help='Call queue this number is assigned to'
    )
