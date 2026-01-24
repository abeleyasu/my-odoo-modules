# -*- coding: utf-8 -*-
"""
RingCentral Call Model
======================

Model for storing call detail records (CDR) and managing call lifecycle.
"""

import logging
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class RingCentralCall(models.Model):
    """RingCentral Call Record"""
    
    _name = 'ringcentral.call'
    _description = 'RingCentral Call'
    _order = 'start_time desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    # ===========================
    # Constraints
    # ===========================
    
    @api.constrains('start_time', 'end_time')
    def _check_time_sequence(self):
        """Ensure end_time is after start_time"""
        for call in self:
            if call.start_time and call.end_time:
                if call.end_time < call.start_time:
                    raise ValidationError(
                        _("End time cannot be before start time.")
                    )
    
    @api.constrains('duration')
    def _check_duration_positive(self):
        """Ensure duration is not negative"""
        for call in self:
            if call.duration is not None and call.duration < 0:
                raise ValidationError(
                    _("Call duration cannot be negative.")
                )
    
    # ===========================
    # Basic Fields
    # ===========================
    
    name = fields.Char(
        string='Call Reference',
        compute='_compute_name',
        store=True
    )
    
    phone_number = fields.Char(
        string='Phone Number',
        required=True,
        index=True,
        tracking=True
    )
    
    phone_number_formatted = fields.Char(
        string='Formatted Number',
        compute='_compute_phone_number_formatted'
    )
    
    direction = fields.Selection([
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
    ], string='Direction', required=True, default='outbound', tracking=True)
    
    state = fields.Selection([
        ('pending', 'Pending'),
        ('ringing', 'Ringing'),
        ('answered', 'Answered'),
        ('on_hold', 'On Hold'),
        ('ended', 'Ended'),
        ('missed', 'Missed'),
        ('failed', 'Failed'),
        ('voicemail', 'Voicemail'),
    ], string='Status', default='pending', required=True, tracking=True)
    
    call_result = fields.Selection([
        ('answered', 'Answered'),
        ('no_answer', 'No Answer'),
        ('busy', 'Busy'),
        ('rejected', 'Rejected'),
        ('voicemail', 'Voicemail'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ], string='Result', tracking=True)
    
    # ===========================
    # RingCentral IDs
    # ===========================
    
    ringcentral_call_id = fields.Char(
        string='RingCentral Call ID',
        index=True,
        readonly=True
    )
    
    ringcentral_session_id = fields.Char(
        string='Telephony Session ID',
        index=True,
        readonly=True
    )
    
    ringcentral_party_id = fields.Char(
        string='Party ID',
        readonly=True
    )
    
    ringout_id = fields.Char(
        string='RingOut ID',
        readonly=True
    )
    
    # ===========================
    # Time Fields
    # ===========================
    
    start_time = fields.Datetime(
        string='Start Time',
        default=fields.Datetime.now,
        required=True,
        index=True
    )
    
    answer_time = fields.Datetime(
        string='Answer Time'
    )
    
    end_time = fields.Datetime(
        string='End Time'
    )
    
    duration = fields.Integer(
        string='Duration (seconds)',
        compute='_compute_duration',
        store=True
    )
    
    duration_display = fields.Char(
        string='Duration',
        compute='_compute_duration_display'
    )
    
    ring_duration = fields.Integer(
        string='Ring Duration (seconds)',
        compute='_compute_ring_duration',
        store=True
    )
    
    # ===========================
    # Related Records
    # ===========================
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Contact',
        index=True,
        tracking=True
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='User',
        default=lambda self: self.env.user,
        index=True,
        tracking=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        index=True
    )
    
    # Polymorphic link to any record
    res_model = fields.Char(
        string='Related Model',
        index=True
    )
    
    res_id = fields.Many2oneReference(
        string='Related Record',
        model_field='res_model',
        index=True
    )
    
    # ===========================
    # Call Control States
    # ===========================
    
    is_muted = fields.Boolean(
        string='Muted',
        default=False
    )
    
    is_recording = fields.Boolean(
        string='Recording',
        default=False
    )
    
    # ===========================
    # Recording
    # ===========================
    
    recording_id = fields.Char(
        string='Recording ID'
    )
    
    recording_url = fields.Char(
        string='Recording URL'
    )
    
    recording_attachment_id = fields.Many2one(
        'ir.attachment',
        string='Recording File'
    )
    
    # ===========================
    # Additional Info
    # ===========================
    
    caller_id_number = fields.Char(
        string='Caller ID Number'
    )
    
    caller_id_name = fields.Char(
        string='Caller ID Name'
    )
    
    call_source = fields.Selection([
        ('api', 'API'),
        ('webrtc', 'WebRTC Softphone'),
        ('embeddable', 'RingCentral Embeddable'),
        ('webhook', 'Webhook'),
        ('manual', 'Manual'),
    ], string='Call Source', default='api')

    # ===========================
    # Chatter Idempotency
    # ===========================

    chatter_start_posted = fields.Boolean(
        string='Chatter Start Posted',
        default=False,
        copy=False,
        readonly=True,
        help='Internal flag to avoid posting duplicate "Call initiated" notes.'
    )

    chatter_end_posted = fields.Boolean(
        string='Chatter End Posted',
        default=False,
        copy=False,
        readonly=True,
        help='Internal flag to avoid posting duplicate call summary notes.'
    )
    
    notes = fields.Text(
        string='Notes'
    )
    
    call_outcome = fields.Selection([
        ('interested', 'Interested'),
        ('callback', 'Callback Requested'),
        ('not_interested', 'Not Interested'),
        ('wrong_number', 'Wrong Number'),
        ('no_decision', 'No Decision'),
    ], string='Outcome', tracking=True)
    
    # ===========================
    # Activity
    # ===========================
    
    activity_id = fields.Many2one(
        'mail.activity',
        string='Activity'
    )
    
    # ===========================
    # Computed Fields
    # ===========================
    
    @api.depends('phone_number', 'direction', 'start_time')
    def _compute_name(self):
        for call in self:
            direction_str = 'Outbound' if call.direction == 'outbound' else 'Inbound'
            date_str = call.start_time.strftime('%Y-%m-%d %H:%M') if call.start_time else ''
            call.name = f"{direction_str} Call - {call.phone_number} - {date_str}"
    
    def _compute_phone_number_formatted(self):
        for call in self:
            # Simple formatting - could use phonenumbers library
            call.phone_number_formatted = call.phone_number
    
    @api.depends('start_time', 'end_time', 'answer_time')
    def _compute_duration(self):
        for call in self:
            if call.answer_time and call.end_time:
                delta = call.end_time - call.answer_time
                call.duration = int(delta.total_seconds())
            else:
                call.duration = 0
    
    @api.depends('duration')
    def _compute_duration_display(self):
        for call in self:
            if call.duration:
                minutes, seconds = divmod(call.duration, 60)
                hours, minutes = divmod(minutes, 60)
                if hours:
                    call.duration_display = f"{hours}:{minutes:02d}:{seconds:02d}"
                else:
                    call.duration_display = f"{minutes}:{seconds:02d}"
            else:
                call.duration_display = "0:00"
    
    @api.depends('start_time', 'answer_time')
    def _compute_ring_duration(self):
        for call in self:
            if call.start_time and call.answer_time:
                delta = call.answer_time - call.start_time
                call.ring_duration = int(delta.total_seconds())
            else:
                call.ring_duration = 0
    
    # ===========================
    # CRUD Methods
    # ===========================
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Auto-detect partner from phone number
            if not vals.get('partner_id') and vals.get('phone_number'):
                partner = self._find_partner_by_phone(vals['phone_number'])
                if partner:
                    vals['partner_id'] = partner.id
        
        calls = super().create(vals_list)
        
        # Send bus notification for new incoming calls
        for call in calls:
            if call.direction == 'inbound' and call.state == 'ringing':
                self._send_incoming_call_notification(call)
        
        return calls
    
    # ===========================
    # Partner Lookup
    # ===========================
    
    @api.model
    def _find_partner_by_phone(self, phone_number):
        """Find partner by phone number"""
        if not phone_number:
            return None
        
        # Clean phone number for search
        clean_number = phone_number.replace('+', '').replace(' ', '').replace('-', '')
        
        # Search in partner phone fields
        partner = self.env['res.partner'].search([
            '|', '|', '|',
            ('phone', 'ilike', clean_number),
            ('mobile', 'ilike', clean_number),
            ('phone', 'ilike', phone_number),
            ('mobile', 'ilike', phone_number),
        ], limit=1)
        
        return partner if partner else None
    
    # ===========================
    # Active Call Methods
    # ===========================
    
    @api.model
    def get_user_active_call(self):
        """Get the current user's active call if any"""
        call = self.search([
            ('user_id', '=', self.env.uid),
            ('state', 'in', ['pending', 'ringing', 'answered', 'on_hold']),
        ], order='start_time desc', limit=1)
        
        if call:
            return call._get_call_data()
        return {}
    
    def _get_call_data(self):
        """Return call data for frontend widget"""
        self.ensure_one()
        return {
            'id': self.id,
            'phone_number': self.phone_number,
            'partner_name': self.partner_id.name if self.partner_id else '',
            'partner_id': self.partner_id.id if self.partner_id else False,
            'direction': self.direction,
            'state': self.state,
            'is_muted': self.is_muted,
            'is_on_hold': self.state == 'on_hold',
            'is_recording': self.is_recording,
            'duration': self.duration,
            'ringout_id': self.ringout_id,
            'session_id': self.ringcentral_session_id,
        }
    
    # ===========================
    # Call Actions
    # ===========================
    
    @api.model
    def action_make_call(self, phone_number, partner_id=None, res_model=None, res_id=None):
        """
        Initiate an outbound call using RingOut
        
        :param phone_number: Number to call
        :param partner_id: Optional partner ID
        :param res_model: Optional related model
        :param res_id: Optional related record ID
        :return: Call record
        """
        api = self.env['ringcentral.api']
        company = self.env.company
        
        # Get caller's number
        user = self.env.user
        from_number = user.ringcentral_direct_number or company.ringcentral_default_caller_id
        
        if not from_number:
            raise UserError(_("No caller ID configured. Please set up your RingCentral extension."))
        
        # Create call record
        call = self.create({
            'phone_number': phone_number,
            'direction': 'outbound',
            'state': 'pending',
            'partner_id': partner_id,
            'res_model': res_model,
            'res_id': res_id,
            'caller_id_number': from_number,
        })
        
        try:
            # Make RingOut call
            result = api.ringout(
                from_number=from_number,
                to_number=phone_number,
                play_prompt=company.ringcentral_call_prompt,
                company=company
            )
            
            call.write({
                'ringout_id': result.get('id'),
                'ringcentral_session_id': result.get('status', {}).get('telephonySessionId'),
                'state': 'ringing',
            })
            
            # Schedule status check
            call._schedule_ringout_status_check()
            
            return {
                'id': call.id,
                'phone_number': phone_number,
                'state': 'ringing',
                'ringout_id': call.ringout_id,
            }
            
        except Exception as e:
            call.write({
                'state': 'failed',
                'call_result': 'failed',
                'notes': str(e),
            })
            raise UserError(_("Failed to initiate call: %s") % str(e))
    
    def action_view_partner_calls(self):
        """View all calls for the current call's partner"""
        self.ensure_one()
        if not self.partner_id:
            return
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Partner Calls'),
            'res_model': 'ringcentral.call',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.partner_id.id)],
            'context': {'default_partner_id': self.partner_id.id},
        }

    def action_view_recordings(self):
        """View recordings for this call"""
        self.ensure_one()
        
        # Try to find recordings linked to this call
        Recording = self.env.get('ringcentral.recording')
        if Recording is None:
            raise UserError(_('Recording module is not installed'))
        
        recordings = Recording.search([('call_id', '=', self.id)])
        
        if len(recordings) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Recording'),
                'res_model': 'ringcentral.recording',
                'view_mode': 'form',
                'res_id': recordings.id,
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Recordings'),
                'res_model': 'ringcentral.recording',
                'view_mode': 'list,form',
                'domain': [('call_id', '=', self.id)],
            }

    def action_open_related_record(self):
        """Open the related record (CRM lead, HR employee, etc.)"""
        self.ensure_one()
        if not self.res_model or not self.res_id:
            return
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Related Record'),
            'res_model': self.res_model,
            'view_mode': 'form',
            'res_id': self.res_id,
        }
    
    def action_answer(self):
        """Answer incoming call (WebRTC mode)"""
        self.ensure_one()
        if self.state != 'ringing':
            return
        
        self.write({
            'state': 'answered',
            'answer_time': fields.Datetime.now(),
        })
        
        # Send bus notification
        self.env['bus.bus']._sendone(
            f'ringcentral_call_{self.user_id.id}',
            'call_answered',
            {'call_id': self.id}
        )
    
    def action_decline(self):
        """Decline incoming call"""
        self.ensure_one()
        if self.state != 'ringing':
            return
        
        self.write({
            'state': 'ended',
            'call_result': 'rejected',
            'end_time': fields.Datetime.now(),
        })
    
    def action_hangup(self):
        """End current call"""
        self.ensure_one()
        
        if self.ringcentral_session_id and self.ringcentral_party_id:
            api = self.env['ringcentral.api']
            try:
                # Use call control API to end call
                pass  # RingCentral doesn't have direct hangup, call ends naturally
            except Exception as e:
                _logger.warning("Failed to hangup via API: %s", str(e))
        
        self.write({
            'state': 'ended',
            'end_time': fields.Datetime.now(),
            'call_result': 'answered' if self.answer_time else 'cancelled',
        })
        
        # Create activity for follow-up
        if self.partner_id and self.duration > 0:
            self._create_call_activity()
    
    def action_toggle_hold(self):
        """Toggle hold status"""
        self.ensure_one()
        
        if not self.ringcentral_session_id or not self.ringcentral_party_id:
            raise UserError(_("No active call session"))
        
        api = self.env['ringcentral.api']
        
        try:
            if self.state == 'on_hold':
                api.call_control_unhold(self.ringcentral_session_id, self.ringcentral_party_id)
                self.write({'state': 'answered'})
            else:
                api.call_control_hold(self.ringcentral_session_id, self.ringcentral_party_id)
                self.write({'state': 'on_hold'})
        except Exception as e:
            raise UserError(_("Failed to toggle hold: %s") % str(e))
    
    def action_toggle_mute(self):
        """Toggle mute status"""
        self.ensure_one()
        
        if not self.ringcentral_session_id or not self.ringcentral_party_id:
            raise UserError(_("No active call session"))
        
        api = self.env['ringcentral.api']
        
        try:
            if self.is_muted:
                api.call_control_unmute(self.ringcentral_session_id, self.ringcentral_party_id)
            else:
                api.call_control_mute(self.ringcentral_session_id, self.ringcentral_party_id)
            
            self.write({'is_muted': not self.is_muted})
        except Exception as e:
            raise UserError(_("Failed to toggle mute: %s") % str(e))
    
    def action_transfer(self, to_number):
        """Transfer call to another number"""
        self.ensure_one()
        
        if not self.ringcentral_session_id or not self.ringcentral_party_id:
            raise UserError(_("No active call session"))
        
        api = self.env['ringcentral.api']
        
        try:
            api.call_control_transfer(
                self.ringcentral_session_id,
                self.ringcentral_party_id,
                to_number
            )
            
            self.write({
                'state': 'ended',
                'end_time': fields.Datetime.now(),
                'notes': f"Transferred to {to_number}",
            })
        except Exception as e:
            raise UserError(_("Failed to transfer call: %s") % str(e))
    
    def action_start_recording(self):
        """Start call recording"""
        self.ensure_one()
        
        if not self.ringcentral_session_id or not self.ringcentral_party_id:
            raise UserError(_("No active call session"))
        
        api = self.env['ringcentral.api']
        
        try:
            result = api.call_control_start_recording(
                self.ringcentral_session_id,
                self.ringcentral_party_id
            )
            
            self.write({
                'is_recording': True,
                'recording_id': result.get('id'),
            })
        except Exception as e:
            raise UserError(_("Failed to start recording: %s") % str(e))
    
    def action_stop_recording(self):
        """Stop call recording"""
        self.ensure_one()
        
        if not self.recording_id:
            return
        
        api = self.env['ringcentral.api']
        
        try:
            api.call_control_stop_recording(
                self.ringcentral_session_id,
                self.ringcentral_party_id,
                self.recording_id
            )
            
            self.write({'is_recording': False})
        except Exception as e:
            raise UserError(_("Failed to stop recording: %s") % str(e))
    
    # ===========================
    # RingOut Status Check
    # ===========================
    
    def _schedule_ringout_status_check(self):
        """Schedule delayed check of RingOut status"""
        self.ensure_one()
        # In production, would use ir.cron or queue.job
        # For now, we rely on webhooks
        pass
    
    def action_check_ringout_status(self):
        """Check RingOut call status"""
        self.ensure_one()
        
        if not self.ringout_id:
            return
        
        api = self.env['ringcentral.api']
        
        try:
            result = api.ringout_status(self.ringout_id)
            status = result.get('status', {}).get('callStatus')
            
            if status == 'Success':
                self.write({
                    'state': 'answered',
                    'answer_time': fields.Datetime.now(),
                    'call_result': 'answered',
                })
            elif status in ('CannotReach', 'NoAnsweringMachine', 'Error'):
                self.write({
                    'state': 'failed',
                    'call_result': 'failed',
                    'end_time': fields.Datetime.now(),
                })
            elif status == 'InProgress':
                self.write({'state': 'ringing'})
            
        except Exception as e:
            _logger.error("Failed to check RingOut status: %s", str(e))
    
    # ===========================
    # Webhook Processing
    # ===========================
    
    @api.model
    def process_telephony_event(self, data, company):
        """
        Process telephony session webhook event with race condition prevention.
        
        Uses database locking to prevent duplicate records when multiple
        webhooks arrive for the same call.
        
        :param data: Webhook event data
        :param company: Company record
        """
        body = data.get('body', {})
        session_id = body.get('telephonySessionId')
        parties = body.get('parties', [])
        
        if not session_id:
            _logger.warning("Telephony event without session ID")
            return
        
        for party in parties:
            phone_number = party.get('from', {}).get('phoneNumber') or party.get('to', {}).get('phoneNumber')
            party_id = party.get('id')
            direction = party.get('direction', '').lower()
            status_code = party.get('status', {}).get('code', '')
            
            if not party_id:
                continue
            
            # Use savepoint for transaction isolation
            try:
                with self.env.cr.savepoint():
                    # Find existing call record (lock for update)
                    call = self.search([
                        ('ringcentral_session_id', '=', session_id),
                        ('ringcentral_party_id', '=', party_id),
                    ], limit=1)
                    
                    if not call and direction == 'inbound' and status_code in ('Setup', 'Proceeding'):
                        # New inbound call - create with explicit lock check
                        # Double-check doesn't exist (concurrent webhook protection)
                        self.env.cr.execute("""
                            SELECT id FROM ringcentral_call 
                            WHERE ringcentral_session_id = %s AND ringcentral_party_id = %s
                            FOR UPDATE SKIP LOCKED
                        """, (session_id, party_id))
                        
                        if self.env.cr.fetchone():
                            continue  # Another process is handling this
                        
                        call = self.create({
                            'phone_number': party.get('from', {}).get('phoneNumber', ''),
                            'direction': 'inbound',
                            'state': 'ringing',
                            'ringcentral_session_id': session_id,
                            'ringcentral_party_id': party_id,
                            'caller_id_number': party.get('from', {}).get('phoneNumber'),
                            'caller_id_name': party.get('from', {}).get('name'),
                            'company_id': company.id,
                        })
                        
                        # Send incoming call notification
                        self._send_incoming_call_notification(call)
                    
                    elif call:
                        # Update existing call
                        vals = self._get_call_update_vals(party, call)
                        
                        if vals:
                            call.write(vals)
                            
                            # Create activity when call ends
                            if vals.get('state') == 'ended' and call.partner_id:
                                call._create_call_activity()

                            # Attempt to sync call recordings (RingCentral recordings can appear with latency)
                            if vals.get('state') == 'ended':
                                try:
                                    call._sync_recordings_from_call_log()
                                except Exception as e:
                                    _logger.info("Recording sync deferred for call %s: %s", call.id, str(e))
                                
            except Exception as e:
                _logger.error("Error processing party %s: %s", party_id, str(e))
                continue
    
    def _get_call_update_vals(self, party, call):
        """
        Get update values for a call from party data.
        
        Separated for cleaner code and testing.
        """
        vals = {}
        status_code = party.get('status', {}).get('code', '')
        
        if status_code == 'Answered':
            vals['state'] = 'answered'
            if not call.answer_time:
                vals['answer_time'] = fields.Datetime.now()
        elif status_code == 'Hold':
            vals['state'] = 'on_hold'
        elif status_code == 'Disconnected':
            vals['state'] = 'ended'
            if not call.end_time:
                vals['end_time'] = fields.Datetime.now()
            
            # Determine result
            reason = party.get('status', {}).get('reason', '')
            if 'Voicemail' in reason:
                vals['call_result'] = 'voicemail'
            elif call.answer_time:
                vals['call_result'] = 'answered'
            else:
                vals['call_result'] = 'no_answer'
        
        # Recording info
        if party.get('recordings'):
            rec = party['recordings'][0]
            vals['recording_id'] = rec.get('id')
            vals['is_recording'] = rec.get('active', False)
        
        return vals
    
    @classmethod
    def _send_incoming_call_notification(cls, call):
        """Send bus notification for incoming call"""
        # Determine which user should receive the notification
        user_id = call.user_id.id if call.user_id else None
        
        if user_id:
            call.env['bus.bus']._sendone(
                f'ringcentral_call_{user_id}',
                'incoming_call',
                {
                    'call_id': call.id,
                    'phone_number': call.phone_number,
                    'caller_name': call.partner_id.name if call.partner_id else call.caller_id_name,
                    'partner_id': call.partner_id.id if call.partner_id else None,
                    'type': 'incoming',
                }
            )
    
    # ===========================
    # Activity Creation
    # ===========================
    
    def _create_call_activity(self):
        """Create activity record for completed call"""
        self.ensure_one()
        
        activity_type = self.env.ref('ringcentral_call.mail_activity_type_phone_call', raise_if_not_found=False)
        if not activity_type:
            return
        
        # Determine the record to attach activity to
        if self.res_model and self.res_id:
            res_model = self.res_model
            res_id = self.res_id
        elif self.partner_id:
            res_model = 'res.partner'
            res_id = self.partner_id.id
        else:
            return
        
        # Create activity
        activity = self.env['mail.activity'].create({
            'activity_type_id': activity_type.id,
            'res_model_id': self.env['ir.model']._get_id(res_model),
            'res_id': res_id,
            'user_id': self.user_id.id,
            'summary': f"Call {'from' if self.direction == 'inbound' else 'to'} {self.phone_number}",
            'note': f"Duration: {self.duration_display}\nOutcome: {self.call_outcome or 'Not set'}",
            'date_deadline': fields.Date.today(),
        })
        
        self.write({'activity_id': activity.id})
        
        # Also post to chatter
        record = self.env[res_model].browse(res_id)
        if hasattr(record, 'message_post'):
            if self.call_source == 'embeddable':
                if self.chatter_end_posted:
                    return

            direction = 'Inbound' if self.direction == 'inbound' else 'Outbound'
            result = self.call_result or 'N/A'
            record.message_post(
                body=(
                    f"{direction} call\n"
                    f"Phone: {self.phone_number}\n"
                    f"Duration: {self.duration_display}\n"
                    f"Result: {result}"
                ),
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
    
    # ===========================
    # Call Log Sync
    # ===========================
    
    @api.model
    def sync_call_log(self, days=1, company=None):
        """
        Sync call log from RingCentral with race condition prevention.
        
        Uses database-level locking to prevent duplicate records when both
        webhooks and cron jobs are processing the same call.
        
        :param days: Number of days to sync
        :param company: Company record
        :return: Number of records synced
        """
        company = company or self.env.company
        api = self.env['ringcentral.api']

        ICP = self.env['ir.config_parameter'].sudo()
        last_sync_key = f'ringcentral_call.call_log_last_sync_company_{company.id}'

        def _parse_dt(val):
            if not val:
                return None
            for fmt in ('%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d %H:%M:%S'):
                try:
                    return datetime.strptime(val, fmt)
                except Exception:
                    continue
            return None

        now_utc = datetime.utcnow()

        last_sync_raw = ICP.get_param(last_sync_key)
        last_sync_dt = _parse_dt(last_sync_raw)

        if last_sync_dt:
            # Small overlap to avoid missing records due to clock skew / eventual consistency
            date_from_dt = last_sync_dt - timedelta(minutes=5)
        else:
            date_from_dt = now_utc - timedelta(days=days)

        date_from = date_from_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        date_to = now_utc.strftime('%Y-%m-%dT%H:%M:%SZ')

        synced_count = 0
        
        try:
            per_page = 250
            page = 1
            max_pages = 200

            while page <= max_pages:
                result = api.get_call_log({
                    'dateFrom': date_from,
                    'dateTo': date_to,
                    'view': 'Detailed',
                    'perPage': per_page,
                    'page': page,
                }, company=company)

                records = (result or {}).get('records', []) if isinstance(result, dict) else []

                for record in records:
                    rc_call_id = record.get('id')
                    session_id = record.get('sessionId') or record.get('telephonySessionId')

                    if not rc_call_id and not session_id:
                        continue
                
                    # Use FOR UPDATE SKIP LOCKED to prevent race conditions
                    # This is a PostgreSQL-specific feature for concurrent access
                    try:
                        # First check if already exists (by call_id OR session_id)
                        domain = []
                        if rc_call_id and session_id:
                            domain = [
                                '|',
                                ('ringcentral_call_id', '=', rc_call_id),
                                '&',
                                ('ringcentral_session_id', '=', session_id),
                                ('ringcentral_session_id', '!=', False),
                            ]
                        elif rc_call_id:
                            domain = [('ringcentral_call_id', '=', rc_call_id)]
                        else:
                            domain = [
                                ('ringcentral_session_id', '=', session_id),
                                ('ringcentral_session_id', '!=', False),
                            ]

                        existing = self.search(domain, limit=1)

                        if existing:
                            # Update with additional data if needed
                            vals = {}
                            if not existing.ringcentral_call_id and rc_call_id:
                                vals['ringcentral_call_id'] = rc_call_id
                            if not existing.ringcentral_session_id and session_id:
                                vals['ringcentral_session_id'] = session_id
                            if not existing.recording_id and (record.get('recording') or {}).get('id'):
                                vals['recording_id'] = (record.get('recording') or {}).get('id')
                            if vals:
                                existing.write(vals)

                            self._ensure_recording_from_call_log_record(existing, record)
                            continue

                        # Create with savepoint to handle concurrent inserts
                        with self.env.cr.savepoint():
                            call = self._create_call_from_log(record, company)
                            if call:
                                synced_count += 1
                                self._ensure_recording_from_call_log_record(call, record)

                    except Exception as e:
                        # Log but continue processing other records
                        _logger.warning("Error syncing call %s: %s", rc_call_id, str(e))
                        continue

                paging = (result or {}).get('paging') if isinstance(result, dict) else None
                total_pages = (paging or {}).get('totalPages') if isinstance(paging, dict) else None
                current_page = (paging or {}).get('page') if isinstance(paging, dict) else None

                if total_pages and current_page and current_page < total_pages:
                    page += 1
                    continue

                if records and len(records) >= per_page:
                    page += 1
                    continue

                break

            if page > max_pages:
                _logger.warning("Call log sync hit max pages (%s); consider reducing window for company %s", max_pages, company.name)

            # Mark successful run
            ICP.set_param(last_sync_key, date_to)
            
            _logger.info("Synced %d calls from RingCentral for company %s", synced_count, company.name)
            return synced_count
            
        except Exception as e:
            _logger.error("Failed to sync call log: %s", str(e))
            return 0

    @api.model
    def _ensure_recording_from_call_log_record(self, call, call_log_record):
        """Create ringcentral.recording metadata (if module installed) from a call-log record."""
        if not call or not call.exists():
            return

        if 'ringcentral.recording' not in self.env:
            return

        recording = (call_log_record or {}).get('recording') or {}
        rc_recording_id = recording.get('id')
        content_uri = recording.get('contentUri')
        if not rc_recording_id or not content_uri:
            return

        Recording = self.env['ringcentral.recording'].sudo()
        exists = Recording.search([
            ('ringcentral_recording_id', '=', str(rc_recording_id)),
            ('call_id', '=', call.id),
        ], limit=1)
        if exists:
            return

        rec_vals = {
            'ringcentral_recording_id': str(rc_recording_id),
            'call_id': call.id,
            'partner_id': call.partner_id.id if call.partner_id else False,
            'phone_number': call.phone_number,
            'caller_name': call.caller_id_name,
            'user_id': call.user_id.id,
            'company_id': call.company_id.id,
            'duration': call_log_record.get('duration') or call.duration or 0,
            'ringcentral_content_uri': content_uri,
            'state': 'available',
        }

        start_time = call_log_record.get('startTime')
        if start_time:
            try:
                rec_vals['recording_date'] = fields.Datetime.from_string(start_time)
            except Exception:
                pass
        elif call.start_time:
            rec_vals['recording_date'] = call.start_time

        created = Recording.create(rec_vals)
        if hasattr(created, '_post_recording_link_to_chatter'):
            created._post_recording_link_to_chatter()

    def _sync_recordings_from_call_log(self):
        """Create ringcentral.recording rows for this call from RingCentral call-log metadata."""
        self.ensure_one()

        if 'ringcentral.recording' not in self.env:
            return

        # If we already have at least one recording linked, avoid extra API calls.
        try:
            existing_any = self.env['ringcentral.recording'].sudo().search([
                ('call_id', '=', self.id),
            ], limit=1)
            if existing_any:
                return
        except Exception:
            pass

        if not self.ringcentral_session_id:
            return

        api = self.env['ringcentral.api'].sudo()

        # Best-effort time window to reduce API load
        date_from = None
        date_to = None
        try:
            if self.start_time:
                date_from = (self.start_time - timedelta(hours=12)).strftime('%Y-%m-%dT%H:%M:%SZ')
            if self.end_time:
                date_to = (self.end_time + timedelta(hours=12)).strftime('%Y-%m-%dT%H:%M:%SZ')
        except Exception:
            date_from = None
            date_to = None

        matches = api.find_recordings_for_telephony_session(
            self.ringcentral_session_id,
            company=self.company_id,
            date_from=date_from,
            date_to=date_to,
        )

        if not matches:
            return

        Recording = self.env['ringcentral.recording'].sudo()
        for match in matches:
            call_log = (match or {}).get('call_log') or {}
            recording = (match or {}).get('recording') or {}

            rc_recording_id = recording.get('id')
            content_uri = recording.get('contentUri')
            if not rc_recording_id or not content_uri:
                continue

            exists = Recording.search([
                ('ringcentral_recording_id', '=', str(rc_recording_id)),
                ('call_id', '=', self.id),
            ], limit=1)
            if exists:
                continue

            rec_vals = {
                'ringcentral_recording_id': str(rc_recording_id),
                'call_id': self.id,
                'partner_id': self.partner_id.id if self.partner_id else False,
                'phone_number': self.phone_number,
                'caller_name': self.caller_id_name,
                'user_id': self.user_id.id,
                'company_id': self.company_id.id,
                'duration': call_log.get('duration') or self.duration or 0,
                'ringcentral_content_uri': content_uri,
                # Remote recording exists; download on demand
                'state': 'available',
            }

            start_time = call_log.get('startTime')
            if start_time:
                try:
                    rec_vals['recording_date'] = fields.Datetime.from_string(start_time)
                except Exception:
                    pass
            elif self.start_time:
                rec_vals['recording_date'] = self.start_time

            created = Recording.create(rec_vals)
            if hasattr(created, '_post_recording_link_to_chatter'):
                created._post_recording_link_to_chatter()
    
    @api.model
    def _create_call_from_log(self, record, company):
        """
        Create a call record from RingCentral API call log data.
        
        Separated for easier testing and transaction control.
        """
        direction = record.get('direction', '').lower()
        
        if direction == 'inbound':
            phone_number = record.get('from', {}).get('phoneNumber', '')
        else:
            to_list = record.get('to') or [{}]
            phone_number = to_list[0].get('phoneNumber', '') if to_list else ''
        
        if not phone_number:
            return None
        
        # Map result
        result_map = {
            'Accepted': 'answered',
            'Voicemail': 'voicemail',
            'Missed': 'no_answer',
            'Busy': 'busy',
            'Rejected': 'rejected',
            'Unknown': 'failed',
        }
        call_result = result_map.get(record.get('result'), 'answered')
        
        # Find partner by phone
        partner = self.env['res.partner'].search([
            '|',
            ('phone', 'ilike', phone_number[-10:]),
            ('mobile', 'ilike', phone_number[-10:]),
        ], limit=1)
        
        return self.create({
            'ringcentral_call_id': record.get('id'),
            'ringcentral_session_id': record.get('sessionId'),
            'phone_number': phone_number,
            'direction': direction,
            'state': 'ended',
            'call_result': call_result,
            'start_time': record.get('startTime'),
            'duration': record.get('duration', 0),
            'recording_id': record.get('recording', {}).get('id'),
            'partner_id': partner.id if partner else False,
            'company_id': company.id,
        })
    
    @api.model
    def cron_sync_call_log(self):
        """Cron job to sync call logs"""
        companies = self.env['res.company'].search([
            ('ringcentral_enabled', '=', True)
        ])
        
        for company in companies:
            self.sync_call_log(days=1, company=company)
