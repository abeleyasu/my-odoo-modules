# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
import json

_logger = logging.getLogger(__name__)


class AITranscript(models.Model):
    _name = 'ringcentral.ai.transcript'
    _description = 'AI Transcript'
    _order = 'create_date desc'

    # ===========================
    # Constraints
    # ===========================
    
    @api.constrains('confidence')
    def _check_confidence_range(self):
        """Ensure confidence score is in valid range (0.0-1.0)"""
        for record in self:
            if record.confidence is not None:
                if record.confidence < 0.0 or record.confidence > 1.0:
                    raise ValidationError(
                        _("Confidence score must be between 0.0 and 1.0.")
                    )
    
    # ===========================
    # Fields
    # ===========================

    name = fields.Char(
        string='Reference',
        compute='_compute_name',
        store=True,
    )
    
    recording_id = fields.Many2one(
        'ringcentral.recording',
        string='Recording',
        required=True,
        ondelete='cascade',
        index=True,
    )
    call_id = fields.Many2one(
        'ringcentral.call',
        string='Call',
        related='recording_id.call_id',
        store=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Contact',
        related='recording_id.partner_id',
        store=True,
    )
    
    # Transcript
    transcript_text = fields.Text(string='Full Transcript')
    transcript_segments = fields.Text(
        string='Segments (JSON)',
        help='Time-stamped transcript segments',
    )
    language = fields.Char(string='Language', default='en-US')
    confidence = fields.Float(string='Confidence Score')
    
    # AI Analysis
    sentiment = fields.Selection([
        ('very_positive', 'Very Positive'),
        ('positive', 'Positive'),
        ('neutral', 'Neutral'),
        ('negative', 'Negative'),
        ('very_negative', 'Very Negative'),
    ], string='Overall Sentiment')
    
    sentiment_score = fields.Float(
        string='Sentiment Score',
        help='-1 (negative) to +1 (positive)',
    )
    
    # Topics
    topics = fields.Text(string='Key Topics (JSON)')
    topics_display = fields.Char(
        string='Topics',
        compute='_compute_topics_display',
    )
    
    # Action Items
    action_items = fields.Text(string='Action Items (JSON)')
    action_items_count = fields.Integer(
        string='Action Items',
        compute='_compute_action_items_count',
    )
    
    # Summary
    summary = fields.Text(string='AI Summary')
    
    # Processing Status
    state = fields.Selection([
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ], string='Status', default='pending')
    
    error_message = fields.Text(string='Error Message')
    processing_time = fields.Float(string='Processing Time (s)')

    @api.depends('recording_id', 'recording_id.display_name')
    def _compute_name(self):
        for record in self:
            if record.recording_id:
                record.name = f'Transcript - {record.recording_id.display_name}'
            else:
                record.name = 'New Transcript'

    @api.depends('topics')
    def _compute_topics_display(self):
        for record in self:
            if record.topics:
                try:
                    topics_list = json.loads(record.topics)
                    record.topics_display = ', '.join(topics_list[:5])
                except Exception:
                    record.topics_display = ''
            else:
                record.topics_display = ''

    @api.depends('action_items')
    def _compute_action_items_count(self):
        for record in self:
            if record.action_items:
                try:
                    items = json.loads(record.action_items)
                    record.action_items_count = len(items)
                except Exception:
                    record.action_items_count = 0
            else:
                record.action_items_count = 0

    def action_process_transcript(self):
        """
        Process recording with AI
        
        Can be called on a recordset. Will process each record individually.
        """
        for record in self:
            record._process_single_transcript()
    
    def _process_single_transcript(self):
        """Process a single transcript record with AI"""
        self.ensure_one()

        # Metadata-only design: do not require storing audio in Odoo.
        # Prefer existing transcription on the recording, otherwise request it from RingCentral.
        if self.recording_id and self.recording_id.transcription:
            self.write({
                'transcript_text': self.recording_id.transcription,
                'state': 'completed',
            })
            self._analyze_completed_transcript()
            return

        self.state = 'processing'
        
        try:
            import time
            start_time = time.time()
            
            rc_api = self.env['ringcentral.api'].sudo()

            result = rc_api.request_transcription(
                self.recording_id.ringcentral_recording_id,
                content_uri=self.recording_id.ringcentral_content_uri,
                language=self.language or 'en-US',
                company=self.recording_id.company_id,
            ) or {}

            transcript_text = result.get('transcription') or result.get('text') or result.get('transcript')
            if transcript_text:
                self.write({
                    'transcript_text': transcript_text,
                    'transcript_segments': json.dumps(result.get('segments', [])) if result.get('segments') else False,
                    'confidence': result.get('confidence', 0.0),
                    'state': 'completed',
                })
                self._analyze_completed_transcript()
                self.processing_time = time.time() - start_time
                return

            job_id = result.get('jobId')
            if job_id:
                self.write({
                    'transcription_job_id': job_id,
                    'state': 'processing',
                })
                self.processing_time = time.time() - start_time
                return

            raise UserError(_('No transcription available yet'))
            
            # Note: analysis is executed in _analyze_completed_transcript()
            
        except Exception as e:
            _logger.error(f'Transcription failed: {e}')
            self.state = 'failed'
            self.error_message = str(e)
    
    # Field for tracking async job
    transcription_job_id = fields.Char(string='Transcription Job ID', readonly=True)
    
    @api.model
    def cron_process_pending_transcripts(self):
        """
        Cron job to process pending transcription jobs.
        
        Checks status of submitted jobs and updates completed ones.
        """
        pending = self.search([
            ('state', '=', 'processing'),
            ('transcription_job_id', '!=', False),
        ])

        rc_api = self.env['ringcentral.api'].sudo()
        
        for transcript in pending:
            try:
                # If recording already has a transcription, use it.
                if transcript.recording_id and transcript.recording_id.transcription:
                    transcript.write({
                        'transcript_text': transcript.recording_id.transcription,
                        'state': 'completed',
                    })
                    transcript._analyze_completed_transcript()
                    continue

                result = rc_api.get_transcription_job(
                    transcript.transcription_job_id,
                    company=transcript.recording_id.company_id if transcript.recording_id else None,
                ) or {}

                status = (result.get('status') or result.get('jobStatus') or '').lower()
                if status in ('completed', 'succeeded', 'success', 'done') or (not status and (result.get('text') or result.get('transcript'))):
                    text = result.get('text') or result.get('transcript')
                    if not text and isinstance(result.get('result'), dict):
                        text = result['result'].get('text') or result['result'].get('transcript')

                    if text:
                        transcript.write({
                            'transcript_text': text,
                            'state': 'completed',
                        })
                        transcript._analyze_completed_transcript()
                elif status in ('failed', 'error'):
                    transcript.write({'state': 'failed', 'error_message': result.get('error') or result.get('message') or 'Transcription failed'})
                    
            except Exception as e:
                _logger.error("Error checking transcript %s: %s", transcript.id, str(e))
    
    def _analyze_completed_transcript(self):
        """Run analysis on completed transcript"""
        self.ensure_one()
        
        if not self.transcript_text:
            return
        
        try:
            # Analyze sentiment
            sentiment_result = self._analyze_sentiment(self.transcript_text)
            
            # Extract topics and action items
            vals = {
                'sentiment': sentiment_result.get('sentiment'),
                'sentiment_score': sentiment_result.get('score', 0.0),
                'topics': json.dumps(self._extract_topics(self.transcript_text)),
                'action_items': json.dumps(self._detect_action_items(self.transcript_text)),
                'summary': self._generate_summary(self.transcript_text),
            }
            
            self.write(vals)
            
            # Update recording transcription field
            if self.recording_id:
                self.recording_id.transcription = self.transcript_text
                
        except Exception as e:
            _logger.error("Analysis error for transcript %s: %s", self.id, str(e))

    def _analyze_sentiment(self, text):
        """Analyze sentiment of transcript"""
        if not text:
            return {'sentiment': 'neutral', 'score': 0.0}
        
        # Placeholder - in production, use NLP service
        # Simple keyword-based analysis as example
        positive_words = ['great', 'excellent', 'thank', 'happy', 'perfect', 'appreciate']
        negative_words = ['problem', 'issue', 'unhappy', 'frustrated', 'bad', 'wrong']
        
        text_lower = text.lower()
        positive_count = sum(1 for w in positive_words if w in text_lower)
        negative_count = sum(1 for w in negative_words if w in text_lower)
        
        score = (positive_count - negative_count) / max(positive_count + negative_count, 1)
        
        if score >= 0.5:
            sentiment = 'very_positive'
        elif score >= 0.2:
            sentiment = 'positive'
        elif score <= -0.5:
            sentiment = 'very_negative'
        elif score <= -0.2:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'
        
        return {'sentiment': sentiment, 'score': score}

    def _extract_topics(self, text):
        """Extract key topics from transcript"""
        if not text:
            return []
        
        # Placeholder - in production, use NLP/topic modeling
        return []

    def _detect_action_items(self, text):
        """Detect action items from transcript"""
        if not text:
            return []
        
        # Placeholder - in production, use NLP
        action_items = []
        
        # Simple pattern matching example
        action_patterns = [
            'will send', 'will call', 'will email', 
            'need to', 'follow up', 'schedule',
        ]
        
        lines = text.split('.')
        for line in lines:
            line_lower = line.lower()
            for pattern in action_patterns:
                if pattern in line_lower:
                    action_items.append({
                        'text': line.strip(),
                        'type': 'action',
                    })
                    break
        
        return action_items

    def _generate_summary(self, text):
        """Generate AI summary of transcript"""
        if not text:
            return ''
        
        # Placeholder - in production, use summarization model
        # Return first few sentences as simple summary
        sentences = text.split('.')[:3]
        return '. '.join(s.strip() for s in sentences if s.strip()) + '.'

    def action_retry(self):
        """Retry failed transcription"""
        self.ensure_one()
        self.state = 'pending'
        self.error_message = False
        self.action_process_transcript()

    def get_segments_formatted(self):
        """Get formatted transcript segments"""
        self.ensure_one()
        if not self.transcript_segments:
            return []
        
        try:
            return json.loads(self.transcript_segments)
        except Exception:
            return []

    def get_action_items_list(self):
        """Get action items as list"""
        self.ensure_one()
        if not self.action_items:
            return []
        
        try:
            return json.loads(self.action_items)
        except Exception:
            return []
