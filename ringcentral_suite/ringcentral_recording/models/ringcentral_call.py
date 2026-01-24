# -*- coding: utf-8 -*-

from odoo import models, fields, api


class RingCentralCall(models.Model):
    _inherit = 'ringcentral.call'

    # Recording relation
    recording_ids = fields.One2many(
        'ringcentral.recording',
        'call_id',
        string='Recordings',
    )
    recording_count = fields.Integer(
        compute='_compute_recording_count',
        string='Recordings',
    )
    
    # Recording state
    is_recording = fields.Boolean(
        string='Currently Recording',
        default=False,
    )
    recording_enabled = fields.Boolean(
        string='Recording Enabled',
        compute='_compute_recording_enabled',
    )

    @api.depends('recording_ids')
    def _compute_recording_count(self):
        for call in self:
            call.recording_count = len(call.recording_ids)

    def _compute_recording_enabled(self):
        for call in self:
            call.recording_enabled = self.env.company.rc_enable_recording

    def action_start_recording(self):
        """Start recording the call"""
        self.ensure_one()
        
        if not self.telephony_session_id:
            return
        
        rc_api = self.env['ringcentral.api'].sudo()
        result = rc_api.start_recording(self.telephony_session_id)
        
        if result:
            self.is_recording = True
            # Create pending recording
            self.env['ringcentral.recording'].create({
                'call_id': self.id,
                'ringcentral_recording_id': result.get('recordingId'),
                'recording_type': 'on_demand',
                'state': 'pending',
                'partner_id': self.partner_id.id,
                'phone_number': self.phone_number,
                'user_id': self.user_id.id,
            })

    def action_stop_recording(self):
        """Stop recording the call"""
        self.ensure_one()
        
        if not self.telephony_session_id:
            return
        
        rc_api = self.env['ringcentral.api'].sudo()
        rc_api.stop_recording(self.telephony_session_id)
        self.is_recording = False

    def action_view_recordings(self):
        """View recordings for this call"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Call Recordings',
            'res_model': 'ringcentral.recording',
            'view_mode': 'tree,form',
            'domain': [('call_id', '=', self.id)],
            'context': {'default_call_id': self.id},
        }
