# -*- coding: utf-8 -*-
"""
RingCentral Company Extension
=============================

Extension of res.company for RingCentral configuration storage.
Implements secure credential storage with encryption.
"""

import base64
import hashlib
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    """Company extension for RingCentral configuration"""
    
    _inherit = 'res.company'
    
    # ===========================
    # Encryption Helpers
    # ===========================
    
    def _get_encryption_key(self):
        """Get or generate encryption key for sensitive data"""
        ICP = self.env['ir.config_parameter'].sudo()
        key = ICP.get_param('ringcentral.encryption_key')
        if not key:
            # Generate new key and store it
            key = Fernet.generate_key().decode()
            ICP.set_param('ringcentral.encryption_key', key)
        return key.encode()
    
    def _encrypt_value(self, value):
        """Encrypt a string value"""
        if not value:
            return ''
        try:
            f = Fernet(self._get_encryption_key())
            return f.encrypt(value.encode()).decode()
        except Exception as e:
            _logger.error("Encryption failed: %s", str(e))
            return value
    
    def _decrypt_value(self, encrypted_value):
        """Decrypt an encrypted string value"""
        if not encrypted_value:
            return ''
        try:
            f = Fernet(self._get_encryption_key())
            return f.decrypt(encrypted_value.encode()).decode()
        except Exception as e:
            # If decryption fails, value might be plain text (migration)
            _logger.warning("Decryption failed, returning as-is: %s", str(e))
            return encrypted_value
    
    # ===========================
    # Enable/Disable
    # ===========================
    
    ringcentral_enabled = fields.Boolean(
        string='RingCentral Enabled',
        default=False,
        help='Enable RingCentral integration for this company'
    )
    
    ringcentral_production_mode = fields.Boolean(
        string='Production Mode',
        default=False,
        help='Enable production mode - requires webhook secret'
    )
    
    # ===========================
    # Authentication - JWT (Encrypted Storage)
    # ===========================
    
    ringcentral_client_id = fields.Char(
        string='RingCentral Client ID',
        help='RingCentral App Client ID'
    )
    
    # Encrypted storage fields (internal)
    _ringcentral_client_secret_encrypted = fields.Char(
        string='Client Secret (Encrypted)',
        groups='ringcentral_base.group_ringcentral_admin'
    )
    
    _ringcentral_jwt_token_encrypted = fields.Char(
        string='JWT Token (Encrypted)',
        groups='ringcentral_base.group_ringcentral_admin'
    )
    
    _ringcentral_password_encrypted = fields.Char(
        string='Password (Encrypted)',
        groups='ringcentral_base.group_ringcentral_admin'
    )
    
    # Computed fields for getting/setting encrypted values
    ringcentral_client_secret = fields.Char(
        string='RingCentral Client Secret',
        compute='_compute_client_secret',
        inverse='_inverse_client_secret',
        help='RingCentral App Client Secret (stored encrypted)'
    )
    
    ringcentral_jwt_token = fields.Char(
        string='RingCentral JWT Token',
        compute='_compute_jwt_token',
        inverse='_inverse_jwt_token',
        help='JWT credential for authentication (stored encrypted)'
    )
    
    ringcentral_password = fields.Char(
        string='RingCentral Password',
        compute='_compute_password',
        inverse='_inverse_password',
        help='Account password (stored encrypted)'
    )
    
    @api.depends('_ringcentral_client_secret_encrypted')
    def _compute_client_secret(self):
        for company in self:
            company.ringcentral_client_secret = company._decrypt_value(
                company._ringcentral_client_secret_encrypted
            )
    
    def _inverse_client_secret(self):
        for company in self:
            company._ringcentral_client_secret_encrypted = company._encrypt_value(
                company.ringcentral_client_secret
            )
    
    @api.depends('_ringcentral_jwt_token_encrypted')
    def _compute_jwt_token(self):
        for company in self:
            company.ringcentral_jwt_token = company._decrypt_value(
                company._ringcentral_jwt_token_encrypted
            )
    
    def _inverse_jwt_token(self):
        for company in self:
            company._ringcentral_jwt_token_encrypted = company._encrypt_value(
                company.ringcentral_jwt_token
            )
    
    @api.depends('_ringcentral_password_encrypted')
    def _compute_password(self):
        for company in self:
            company.ringcentral_password = company._decrypt_value(
                company._ringcentral_password_encrypted
            )
    
    def _inverse_password(self):
        for company in self:
            company._ringcentral_password_encrypted = company._encrypt_value(
                company.ringcentral_password
            )
    
    # ===========================
    # Authentication - OAuth
    # ===========================
    
    ringcentral_username = fields.Char(
        string='RingCentral Username',
        help='Account username (phone number)'
    )
    
    ringcentral_extension = fields.Char(
        string='RingCentral Extension',
        help='Extension number'
    )
    
    # ===========================
    # Account Info (synced from RingCentral)
    # ===========================
    
    ringcentral_account_id = fields.Char(
        string='RingCentral Account ID',
        readonly=True,
        help='Account ID from RingCentral (used for webhook routing)'
    )
    
    # ===========================
    # Server Configuration
    # ===========================
    
    ringcentral_server_url_selection = fields.Selection([
        ('https://platform.ringcentral.com', 'Production'),
        ('https://platform.devtest.ringcentral.com', 'Sandbox'),
    ], string='RingCentral Environment',
       default='https://platform.ringcentral.com',
       help='API environment')
    
    ringcentral_server_url = fields.Char(
        string='RingCentral Server URL',
        compute='_compute_server_url',
        store=True
    )
    
    @api.depends('ringcentral_server_url_selection')
    def _compute_server_url(self):
        for company in self:
            company.ringcentral_server_url = company.ringcentral_server_url_selection or 'https://platform.ringcentral.com'
    
    # ===========================
    # Webhook Configuration
    # ===========================
    
    ringcentral_webhook_url = fields.Char(
        string='Webhook URL',
        help='URL for webhook notifications'
    )
    
    ringcentral_webhook_secret = fields.Char(
        string='Webhook Secret',
        help='Secret for webhook signature validation'
    )
    
    ringcentral_subscription_id = fields.Char(
        string='Subscription ID',
        help='RingCentral webhook subscription ID'
    )
    
    # ===========================
    # Default Settings
    # ===========================
    
    ringcentral_default_caller_id = fields.Char(
        string='Default Caller ID',
        help='Default outbound caller ID'
    )
    
    ringcentral_auto_record_calls = fields.Boolean(
        string='Auto-Record Calls',
        default=False,
        help='Automatically record outbound calls'
    )
    
    ringcentral_call_prompt = fields.Boolean(
        string='Play Connection Prompt',
        default=True,
        help='Play prompt when RingOut connects'
    )
    
    # ===========================
    # Phone Numbers
    # ===========================
    
    ringcentral_phone_numbers = fields.Text(
        string='Phone Numbers',
        help='Available phone numbers (synced from RingCentral)'
    )
    
    # ===========================
    # Health Status
    # ===========================
    
    ringcentral_health_status = fields.Selection([
        ('healthy', 'Healthy'),
        ('unhealthy', 'Unhealthy'),
        ('error', 'Error'),
        ('unknown', 'Unknown'),
    ], string='Health Status',
       default='unknown',
       help='Connection health status')
    
    ringcentral_last_health_check = fields.Datetime(
        string='Last Health Check'
    )
    
    ringcentral_health_latency = fields.Float(
        string='API Latency (ms)',
        help='Last measured API latency'
    )
    
    # ===========================
    # Recording Compliance
    # ===========================
    
    ringcentral_recording_consent_type = fields.Selection([
        ('none', 'No Recording'),
        ('one_party', 'One-Party Consent (Beep)'),
        ('two_party', 'Two-Party Consent (Verbal)'),
    ], string='Recording Consent Type',
       default='one_party',
       help='Recording consent requirement based on jurisdiction')
    
    ringcentral_recording_retention_days = fields.Integer(
        string='Recording Retention (days)',
        default=365,
        help='Days to retain call recordings'
    )
    
    # ===========================
    # Rate Limiting Configuration
    # ===========================
    
    ringcentral_max_retries = fields.Integer(
        string='Max API Retries',
        default=3,
        help='Maximum number of API retry attempts'
    )
    
    ringcentral_retry_delay = fields.Integer(
        string='Retry Delay (seconds)',
        default=1,
        help='Base delay between retries (uses exponential backoff)'
    )
    
    ringcentral_rate_limit_wait = fields.Integer(
        string='Rate Limit Wait (seconds)',
        default=60,
        help='Wait time when rate limited'
    )
    
    # ===========================
    # Webhook IP Allowlist
    # ===========================
    
    ringcentral_webhook_ip_allowlist = fields.Text(
        string='Webhook IP Allowlist',
        default='104.146.0.0/16\n35.190.0.0/16\n35.186.0.0/16',
        help='Comma or newline separated list of allowed IP ranges for webhooks'
    )
    
    # ===========================
    # Subscription Management
    # ===========================
    
    ringcentral_subscription_expires = fields.Datetime(
        string='Subscription Expires',
        help='When the webhook subscription expires'
    )
    
    # ===========================
    # Validation Methods
    # ===========================
    
    @api.constrains('ringcentral_enabled', 'ringcentral_production_mode', 'ringcentral_webhook_secret')
    def _check_production_requirements(self):
        """Ensure production mode has proper security configured"""
        for company in self:
            if company.ringcentral_enabled and company.ringcentral_production_mode:
                if not company.ringcentral_webhook_secret:
                    raise UserError(_(
                        "Production mode requires a webhook secret to be configured. "
                        "Please set a webhook secret or disable production mode."
                    ))
    
    @api.constrains('ringcentral_enabled', 'ringcentral_client_id')
    def _check_client_id(self):
        """Ensure client ID is set when enabled"""
        for company in self:
            if company.ringcentral_enabled and not company.ringcentral_client_id:
                raise UserError(_("RingCentral Client ID is required when integration is enabled."))
    
    def action_generate_webhook_secret(self):
        """Generate a secure webhook secret"""
        import secrets
        self.ensure_one()
        self.ringcentral_webhook_secret = secrets.token_urlsafe(32)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Webhook Secret Generated'),
                'message': _('A new secure webhook secret has been generated.'),
                'type': 'success',
            }
        }

