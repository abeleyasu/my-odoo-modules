# -*- coding: utf-8 -*-
"""
RingCentral HR Employee Extension
=================================

Extension of hr.employee for RingCentral integration.
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    """HR Employee extension for RingCentral integration"""
    
    _inherit = 'hr.employee'
    
    # ===========================
    # Communication Statistics
    # ===========================
    
    call_count = fields.Integer(
        compute='_compute_communication_stats',
        string='Calls',
    )
    
    sms_count = fields.Integer(
        compute='_compute_communication_stats',
        string='SMS',
    )
    
    last_call_date = fields.Datetime(
        compute='_compute_last_communication',
        string='Last Call',
    )
    
    last_sms_date = fields.Datetime(
        compute='_compute_last_communication',
        string='Last SMS',
    )
    
    # ===========================
    # RingCentral Extension Info
    # ===========================
    
    ringcentral_extension = fields.Char(
        string='RingCentral Extension',
        help='RingCentral extension number for this employee'
    )
    
    ringcentral_direct_number = fields.Char(
        string='RingCentral Direct Number',
        help='RingCentral direct dial number'
    )
    
    # ===========================
    # Computed Methods
    # ===========================
    
    def _compute_communication_stats(self):
        """Compute call and SMS statistics for each employee"""
        Call = self.env['ringcentral.call']
        SMS = self.env['ringcentral.sms']
        
        for employee in self:
            domain = employee._get_communication_domain()
            employee.call_count = Call.search_count(domain)
            employee.sms_count = SMS.search_count(domain)
    
    def _compute_last_communication(self):
        """Compute last communication dates"""
        Call = self.env['ringcentral.call']
        SMS = self.env['ringcentral.sms']
        
        for employee in self:
            domain = employee._get_communication_domain()
            
            last_call = Call.search(domain, order='create_date desc', limit=1)
            employee.last_call_date = last_call.create_date if last_call else False
            
            last_sms = SMS.search(domain, order='create_date desc', limit=1)
            employee.last_sms_date = last_sms.create_date if last_sms else False
    
    def _get_communication_domain(self):
        """Get domain for finding communications related to this employee"""
        self.ensure_one()
        
        phones = []
        if self.work_phone:
            phones.append(self.work_phone)
        if self.mobile_phone:
            phones.append(self.mobile_phone)
        if self.private_phone:
            phones.append(self.private_phone)
        
        if phones:
            return [('phone_number', 'in', phones)]
        else:
            return [('id', '=', 0)]  # Impossible domain
    
    # ===========================
    # Actions
    # ===========================
    
    def action_call(self):
        """Quick call action for employee - shows call control widget"""
        self.ensure_one()
        
        phone = self.work_phone or self.mobile_phone or self.private_phone
        
        if not phone:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('No phone number available for this employee'),
                    'type': 'warning',
                }
            }
        
        call_model = self.env['ringcentral.call']

        # Odoo versions differ on which partner field exists on hr.employee.
        # Prefer the employee's work contact partner when available.
        partner = (
            getattr(self, 'work_contact_id', False)
            or getattr(self, 'private_address_id', False)
            or getattr(self, 'address_home_id', False)
        )
        
        try:
            # Return client action to use RingCentral Embeddable widget
            return {
                'type': 'ir.actions.client',
                'tag': 'ringcentral_embeddable_call',
                'params': {
                    'phone_number': phone,
                    'partner_name': self.name,
                    'res_model': 'hr.employee',
                    'res_id': self.id,
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Call Failed'),
                    'message': str(e),
                    'type': 'danger',
                }
            }
    
    def action_send_sms(self):
        """Quick SMS action for employee"""
        self.ensure_one()
        
        phone = self.mobile_phone or self.work_phone or self.private_phone
        
        if not phone:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('No phone number available for this employee'),
                    'type': 'warning',
                }
            }
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Send SMS to Employee'),
            'res_model': 'ringcentral.sms.compose',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_phone_number': phone,
                'default_res_model': 'hr.employee',
                'default_res_id': self.id,
            },
        }
    
    def action_schedule_meeting(self):
        """Schedule a RingCentral meeting with employee"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Schedule Meeting'),
            'res_model': 'ringcentral.meeting',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_name': _('Meeting with %s') % self.name,
                'default_employee_id': self.id,
            },
        }
    
    def action_view_calls(self):
        """View all calls for this employee"""
        self.ensure_one()
        
        domain = self._get_communication_domain()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Employee Calls'),
            'res_model': 'ringcentral.call',
            'view_mode': 'tree,form',
            'domain': domain,
            'context': {'default_phone_number': self.work_phone or self.mobile_phone},
        }
    
    def action_view_sms(self):
        """View all SMS for this employee"""
        self.ensure_one()
        
        domain = self._get_communication_domain()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Employee SMS'),
            'res_model': 'ringcentral.sms',
            'view_mode': 'tree,form',
            'domain': domain,
            'context': {'default_phone_number': self.mobile_phone or self.work_phone},
        }
