# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Recording Settings
    rc_enable_recording = fields.Boolean(
        string='Enable Call Recording',
        config_parameter='ringcentral_recording.enable_recording',
        default=True,
    )
    rc_auto_record_all = fields.Boolean(
        string='Auto Record All Calls',
        config_parameter='ringcentral_recording.auto_record_all',
        default=False,
    )
    rc_auto_record_inbound = fields.Boolean(
        string='Auto Record Inbound',
        config_parameter='ringcentral_recording.auto_record_inbound',
        default=False,
    )
    rc_auto_record_outbound = fields.Boolean(
        string='Auto Record Outbound',
        config_parameter='ringcentral_recording.auto_record_outbound',
        default=False,
    )
    rc_auto_download_recordings = fields.Boolean(
        related='company_id.rc_auto_download_recordings',
        readonly=False,
    )
    
    # Retention Settings
    rc_default_retention_policy_id = fields.Many2one(
        'ringcentral.recording.retention',
        string='Default Retention Policy',
        config_parameter='ringcentral_recording.default_retention_policy',
    )
    
    # Transcription Settings
    rc_auto_transcribe = fields.Boolean(
        string='Auto Transcribe Recordings',
        config_parameter='ringcentral_recording.auto_transcribe',
        default=False,
    )
    rc_transcription_language = fields.Selection([
        ('en-US', 'English (US)'),
        ('en-GB', 'English (UK)'),
        ('es-ES', 'Spanish'),
        ('fr-FR', 'French'),
        ('de-DE', 'German'),
        ('it-IT', 'Italian'),
        ('pt-BR', 'Portuguese (Brazil)'),
    ], string='Transcription Language',
        config_parameter='ringcentral_recording.transcription_language',
        default='en-US',
    )
    
    # Consent Settings
    rc_require_consent = fields.Boolean(
        string='Require Recording Consent',
        config_parameter='ringcentral_recording.require_consent',
        default=True,
    )
    rc_consent_announcement = fields.Boolean(
        string='Play Consent Announcement',
        config_parameter='ringcentral_recording.consent_announcement',
        default=True,
    )


class ResCompany(models.Model):
    _inherit = 'res.company'

    rc_auto_download_recordings = fields.Boolean(
        string='Auto Download Recordings',
        default=True,
        help='Automatically download recordings from RingCentral',
    )
