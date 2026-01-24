# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class RingCentralRecording(models.Model):
    _inherit = 'ringcentral.recording'

    # AI Transcripts
    ai_transcript_ids = fields.One2many(
        'ringcentral.ai.transcript',
        'recording_id',
        string='AI Transcripts',
    )
    has_ai_transcript = fields.Boolean(
        string='Has AI Transcript',
        compute='_compute_has_ai_transcript',
        store=True,
    )
    
    # Quick access to latest AI analysis
    ai_sentiment = fields.Selection(
        selection=[
            ('very_positive', 'Very Positive'),
            ('positive', 'Positive'),
            ('neutral', 'Neutral'),
            ('negative', 'Negative'),
            ('very_negative', 'Very Negative'),
        ],
        string='AI Sentiment',
        compute='_compute_ai_sentiment',
        store=True,
    )
    ai_summary = fields.Text(
        string='AI Summary',
        compute='_compute_ai_summary',
    )

    @api.depends('ai_transcript_ids')
    def _compute_has_ai_transcript(self):
        for record in self:
            record.has_ai_transcript = bool(
                record.ai_transcript_ids.filtered(lambda t: t.state == 'completed')
            )

    @api.depends('ai_transcript_ids', 'ai_transcript_ids.summary')
    def _compute_ai_summary(self):
        for record in self:
            completed = record.ai_transcript_ids.filtered(lambda t: t.state == 'completed')
            if completed:
                record.ai_summary = completed[0].summary
            else:
                record.ai_summary = ''

    @api.depends('ai_transcript_ids', 'ai_transcript_ids.state', 'ai_transcript_ids.sentiment')
    def _compute_ai_sentiment(self):
        for record in self:
            completed = record.ai_transcript_ids.filtered(lambda t: t.state == 'completed')
            record.ai_sentiment = completed[0].sentiment if completed else False

    def action_transcribe_with_ai(self):
        """Create and process AI transcript"""
        self.ensure_one()
        
        # Check if already has pending/processing transcript
        existing = self.ai_transcript_ids.filtered(
            lambda t: t.state in ('pending', 'processing')
        )
        if existing:
            return {
                'type': 'ir.actions.act_window',
                'name': _('AI Transcript'),
                'res_model': 'ringcentral.ai.transcript',
                'res_id': existing[0].id,
                'view_mode': 'form',
            }
        
        # Create new transcript
        transcript = self.env['ringcentral.ai.transcript'].create({
            'recording_id': self.id,
        })
        
        # Process in background
        transcript.action_process_transcript()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('AI Transcript'),
            'res_model': 'ringcentral.ai.transcript',
            'res_id': transcript.id,
            'view_mode': 'form',
        }

    def action_view_ai_transcripts(self):
        """View all AI transcripts for this recording"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('AI Transcripts'),
            'res_model': 'ringcentral.ai.transcript',
            'view_mode': 'tree,form',
            'domain': [('recording_id', '=', self.id)],
            'context': {'default_recording_id': self.id},
        }
