# -*- coding: utf-8 -*-
"""
RingCentral API Log Model
=========================

Logging model for all RingCentral API calls for monitoring, debugging, and auditing.
"""

from odoo import api, fields, models


class RingCentralAPILog(models.Model):
    """RingCentral API Call Log"""
    
    _name = 'ringcentral.api.log'
    _description = 'RingCentral API Log'
    _order = 'create_date desc'
    _rec_name = 'endpoint'
    
    method = fields.Selection([
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('DELETE', 'DELETE'),
        ('AUTH', 'AUTH'),
    ], string='Method', required=True, index=True)
    
    endpoint = fields.Char('Endpoint', required=True, index=True)
    request_data = fields.Text('Request Data')
    response_data = fields.Text('Response Data')
    error = fields.Text('Error')
    
    status = fields.Selection([
        ('success', 'Success'),
        ('error', 'Error'),
    ], string='Status', required=True, default='success', index=True)
    
    elapsed_time = fields.Float('Elapsed Time (s)', digits=(10, 4))
    
    company_id = fields.Many2one('res.company', string='Company', 
                                  default=lambda self: self.env.company,
                                  required=True, index=True)
    user_id = fields.Many2one('res.users', string='User',
                               default=lambda self: self.env.user,
                               index=True)
    
    # Computed fields
    elapsed_time_ms = fields.Float('Elapsed Time (ms)', compute='_compute_elapsed_time_ms')
    
    @api.depends('elapsed_time')
    def _compute_elapsed_time_ms(self):
        for record in self:
            record.elapsed_time_ms = record.elapsed_time * 1000
    
    @api.model
    def cleanup_old_logs(self, days=30):
        """Remove API logs older than specified days"""
        cutoff_date = fields.Datetime.subtract(fields.Datetime.now(), days=days)
        old_logs = self.search([('create_date', '<', cutoff_date)])
        count = len(old_logs)
        old_logs.unlink()
        return count
    
    @api.model
    def get_api_stats(self, days=7):
        """Get API usage statistics"""
        cutoff_date = fields.Datetime.subtract(fields.Datetime.now(), days=days)
        
        logs = self.search([('create_date', '>=', cutoff_date)])
        
        total_calls = len(logs)
        success_calls = len(logs.filtered(lambda l: l.status == 'success'))
        error_calls = len(logs.filtered(lambda l: l.status == 'error'))
        
        avg_latency = sum(logs.mapped('elapsed_time_ms')) / total_calls if total_calls else 0
        
        # Group by endpoint
        endpoint_stats = {}
        for log in logs:
            if log.endpoint not in endpoint_stats:
                endpoint_stats[log.endpoint] = {'count': 0, 'errors': 0}
            endpoint_stats[log.endpoint]['count'] += 1
            if log.status == 'error':
                endpoint_stats[log.endpoint]['errors'] += 1
        
        return {
            'period_days': days,
            'total_calls': total_calls,
            'success_calls': success_calls,
            'error_calls': error_calls,
            'success_rate': (success_calls / total_calls * 100) if total_calls else 0,
            'avg_latency_ms': round(avg_latency, 2),
            'endpoint_stats': endpoint_stats,
        }

    @api.model
    def cron_health_check(self):
        """Scheduled health check for RingCentral API - checks recent API calls for issues"""
        import logging
        _logger = logging.getLogger(__name__)
        
        # Get stats from last hour
        from datetime import timedelta
        cutoff = fields.Datetime.now() - timedelta(hours=1)
        recent_logs = self.search([('create_date', '>=', cutoff)])
        
        if recent_logs:
            error_count = len(recent_logs.filtered(lambda l: l.status == 'error'))
            total_count = len(recent_logs)
            error_rate = (error_count / total_count) * 100 if total_count else 0
            
            if error_rate > 50:
                _logger.warning(f"RingCentral API health check: High error rate {error_rate:.1f}% in last hour")
            else:
                _logger.info(f"RingCentral API health check: OK ({total_count} calls, {error_rate:.1f}% errors)")
        else:
            _logger.info("RingCentral API health check: No recent API calls")
        
        return True

    @api.model
    def cron_cleanup_old_logs(self, days=30):
        """Cron job to cleanup old API logs"""
        import logging
        _logger = logging.getLogger(__name__)
        
        count = self.cleanup_old_logs(days=days)
        _logger.info(f"RingCentral API log cleanup: Deleted {count} old logs")
        return True
