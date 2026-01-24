# -*- coding: utf-8 -*-
"""
RingCentral Test Connection Wizard
==================================

Wizard for testing RingCentral connection and displaying results.
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class RingCentralTestConnection(models.TransientModel):
    """Wizard for testing RingCentral connection"""
    
    _name = 'ringcentral.test.connection'
    _description = 'Test RingCentral Connection'
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    
    result = fields.Text('Result', readonly=True)
    status = fields.Selection([
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ], string='Status', default='pending')
    
    account_id = fields.Char('Account ID', readonly=True)
    account_status = fields.Char('Account Status', readonly=True)
    service_plan = fields.Char('Service Plan', readonly=True)
    latency_ms = fields.Float('Latency (ms)', readonly=True)
    
    def action_test(self):
        """Run connection test"""
        self.ensure_one()
        
        api = self.env['ringcentral.api']
        
        try:
            result = api.health_check(self.company_id)
            
            if result['status'] == 'healthy':
                self.write({
                    'status': 'success',
                    'account_id': result['details'].get('account_id', ''),
                    'account_status': result['details'].get('account_status', ''),
                    'service_plan': result['details'].get('service_plan', ''),
                    'latency_ms': result['latency_ms'],
                    'result': _('Connection successful! API responded in %.2f ms.') % result['latency_ms'],
                })
            else:
                self.write({
                    'status': 'failed',
                    'result': _('Connection failed: %s') % result['details'].get('error', 'Unknown error'),
                })
        except Exception as e:
            self.write({
                'status': 'failed',
                'result': _('Connection error: %s') % str(e),
            })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ringcentral.test.connection',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def action_test_ringout(self):
        """Test RingOut functionality"""
        self.ensure_one()
        
        # This is a placeholder - in production, would prompt for numbers
        raise UserError(_("Please configure a test phone number to test RingOut."))
    
    def action_test_sms(self):
        """Test SMS functionality"""
        self.ensure_one()
        
        raise UserError(_("Please configure a test phone number to test SMS."))
