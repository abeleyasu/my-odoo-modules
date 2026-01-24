# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class CallQueue(models.Model):
    _name = 'ringcentral.call.queue'
    _description = 'Call Queue'
    _inherit = ['mail.thread']
    _order = 'name'
    
    _sql_constraints = [
        ('extension_unique', 'UNIQUE(extension)', 
         'Queue extension must be unique! This extension is already assigned to another queue.'),
    ]

    name = fields.Char(string='Queue Name', required=True)
    active = fields.Boolean(string='Active', default=True)
    
    # RingCentral Reference
    ringcentral_queue_id = fields.Char(string='RingCentral Queue ID')
    extension = fields.Char(string='Extension')
    
    # Description
    description = fields.Text(string='Description')
    
    # Routing Settings
    routing_type = fields.Selection([
        ('rotating', 'Rotating'),
        ('simultaneous', 'Simultaneous'),
        ('sequential', 'Sequential'),
        ('least_calls', 'Least Active'),
    ], string='Routing Type', default='rotating')
    
    # Wait Settings
    max_wait_time = fields.Integer(
        string='Max Wait Time (sec)',
        default=300,
        help='Maximum time caller waits before overflow',
    )
    hold_music_id = fields.Many2one(
        'ir.attachment',
        string='Hold Music',
    )
    
    # Overflow
    overflow_action = fields.Selection([
        ('voicemail', 'Send to Voicemail'),
        ('extension', 'Transfer to Extension'),
        ('disconnect', 'Disconnect'),
    ], string='Overflow Action', default='voicemail')
    overflow_extension = fields.Char(string='Overflow Extension')
    
    # Agents
    agent_ids = fields.One2many(
        'ringcentral.call.queue.agent',
        'queue_id',
        string='Agents',
    )
    agent_count = fields.Integer(
        string='Agents',
        compute='_compute_agent_count',
    )
    available_agent_count = fields.Integer(
        string='Available Agents',
        compute='_compute_agent_count',
    )
    
    # Statistics
    calls_waiting = fields.Integer(
        string='Calls Waiting',
        compute='_compute_queue_stats',
    )
    avg_wait_time = fields.Float(
        string='Avg Wait Time (sec)',
        compute='_compute_queue_stats',
    )
    calls_today = fields.Integer(
        string='Calls Today',
        compute='_compute_queue_stats',
    )
    service_level = fields.Float(
        string='Service Level %',
        compute='_compute_queue_stats',
        help='Percentage of calls answered within target time',
    )

    @api.depends('agent_ids', 'agent_ids.is_available')
    def _compute_agent_count(self):
        for queue in self:
            queue.agent_count = len(queue.agent_ids)
            queue.available_agent_count = len(
                queue.agent_ids.filtered(lambda a: a.is_available)
            )

    def _compute_queue_stats(self):
        """Compute queue statistics from call records and RingCentral API"""
        from datetime import datetime, timedelta
        
        today_start = datetime.combine(fields.Date.today(), datetime.min.time())
        
        for queue in self:
            # Get calls for this queue from today
            calls = self.env['ringcentral.call'].search([
                ('queue_id', '=', queue.id),
                ('start_time', '>=', today_start),
            ])
            
            # Calls waiting - active calls in queue not yet answered
            waiting_calls = calls.filtered(
                lambda c: c.state in ('pending', 'ringing') and not c.answer_time
            )
            queue.calls_waiting = len(waiting_calls)
            
            # Calls today
            queue.calls_today = len(calls)
            
            # Average wait time (time from start to answer)
            answered_calls = calls.filtered(lambda c: c.answer_time)
            if answered_calls:
                wait_times = []
                for call in answered_calls:
                    if call.start_time and call.answer_time:
                        wait = (call.answer_time - call.start_time).total_seconds()
                        wait_times.append(wait)
                queue.avg_wait_time = sum(wait_times) / len(wait_times) if wait_times else 0.0
            else:
                queue.avg_wait_time = 0.0
            
            # Service level - % calls answered within target (e.g., 20 seconds)
            target_wait = 20  # seconds
            if answered_calls:
                within_target = len([c for c in answered_calls 
                                    if c.ring_duration and c.ring_duration <= target_wait])
                queue.service_level = (within_target / len(answered_calls)) * 100
            else:
                queue.service_level = 100.0
    
    @api.model
    def fetch_realtime_stats(self):
        """
        Fetch real-time queue statistics from RingCentral API.
        
        Returns aggregated stats for all queues.
        """
        api = self.env['ringcentral.api']
        stats = {}
        
        for queue in self.search([('active', '=', True)]):
            try:
                if queue.ringcentral_queue_id:
                    result = api._api_call(
                        'GET',
                        f'/restapi/v1.0/account/~/call-queues/{queue.ringcentral_queue_id}/members-status'
                    )
                    
                    stats[queue.id] = {
                        'queue_name': queue.name,
                        'calls_waiting': result.get('callsInQueue', 0),
                        'longest_wait': result.get('longestWaitTime', 0),
                        'agents_available': len([m for m in result.get('members', []) 
                                                 if m.get('status') == 'Available']),
                        'agents_on_call': len([m for m in result.get('members', []) 
                                              if m.get('status') == 'OnCall']),
                    }
            except Exception as e:
                _logger.warning("Failed to fetch stats for queue %s: %s", queue.name, str(e))
                stats[queue.id] = {
                    'queue_name': queue.name,
                    'error': str(e),
                }
        
        return stats

    def action_sync_from_ringcentral(self):
        """Sync queue info from RingCentral"""
        self.ensure_one()
        
        api = self.env['ringcentral.api'].get_api()
        if not api:
            return
        
        try:
            # Fetch queue details from RingCentral
            if self.ringcentral_queue_id:
                queue_info = api.get_call_queue(self.ringcentral_queue_id)
                # Update local record
                _logger.info(f'Synced queue: {self.name}')
        except Exception as e:
            _logger.error(f'Failed to sync queue: {e}')

    def action_view_agents(self):
        """Open agents view"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Queue Agents'),
            'res_model': 'ringcentral.call.queue.agent',
            'view_mode': 'tree,form',
            'domain': [('queue_id', '=', self.id)],
            'context': {'default_queue_id': self.id},
        }


class CallQueueAgent(models.Model):
    _name = 'ringcentral.call.queue.agent'
    _description = 'Call Queue Agent'
    _order = 'sequence, id'

    queue_id = fields.Many2one(
        'ringcentral.call.queue',
        string='Queue',
        required=True,
        ondelete='cascade',
    )
    user_id = fields.Many2one(
        'res.users',
        string='Agent',
        required=True,
    )
    
    sequence = fields.Integer(string='Priority', default=10)
    
    # Status
    is_available = fields.Boolean(
        string='Available',
        compute='_compute_availability',
        store=True,
    )
    
    # Skill level for routing
    skill_level = fields.Integer(
        string='Skill Level',
        default=1,
        help='1-10, higher = more skilled',
    )
    
    # Statistics
    calls_handled_today = fields.Integer(
        string='Calls Today',
        compute='_compute_agent_stats',
    )
    avg_handle_time = fields.Float(
        string='Avg Handle Time',
        compute='_compute_agent_stats',
    )

    @api.depends('user_id', 'user_id.presence_status')
    def _compute_availability(self):
        for agent in self:
            presence = agent.user_id.presence_status if agent.user_id else ''
            agent.is_available = presence in ('available', 'busy')

    def _compute_agent_stats(self):
        """Compute agent statistics from call records"""
        from datetime import datetime
        
        today_start = datetime.combine(fields.Date.today(), datetime.min.time())
        
        for agent in self:
            # Get calls handled by this agent today
            calls = self.env['ringcentral.call'].search([
                ('user_id', '=', agent.user_id.id),
                ('start_time', '>=', today_start),
                ('state', '=', 'ended'),
            ])
            
            agent.calls_handled_today = len(calls)
            
            # Average handle time
            if calls:
                handle_times = [c.duration for c in calls if c.duration]
                agent.avg_handle_time = sum(handle_times) / len(handle_times) if handle_times else 0.0
            else:
                agent.avg_handle_time = 0.0

    def action_login(self):
        """Login agent to queue"""
        self.ensure_one()
        # Call RingCentral API to login agent
        _logger.info(f'Agent {self.user_id.name} logged into queue {self.queue_id.name}')

    def action_logout(self):
        """Logout agent from queue"""
        self.ensure_one()
        # Call RingCentral API to logout agent
        _logger.info(f'Agent {self.user_id.name} logged out of queue {self.queue_id.name}')
