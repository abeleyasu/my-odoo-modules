# -*- coding: utf-8 -*-
"""
Phone Common Extension for RingCentral
======================================

Override click2dial to use RingCentral RingOut API.
Provides comprehensive phone number normalization utilities.
"""

import re
import logging
from functools import lru_cache

from odoo import api, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PhoneCommon(models.AbstractModel):
    """Extend phone.common for RingCentral click-to-dial"""
    
    _inherit = 'phone.common'
    
    @api.model
    def click2dial(self, erp_number):
        """
        Override click2dial to use RingCentral RingOut
        
        :param erp_number: Phone number from Odoo record
        :return: Dict with call info
        """
        # Check if RingCentral is enabled
        company = self.env.company
        if not company.ringcentral_enabled:
            # Fall back to parent implementation or tel: link
            return super().click2dial(erp_number)
        
        # Clean the number
        cleaned_number = self._normalize_phone_number(erp_number)
        if not cleaned_number:
            raise UserError(_("Invalid phone number"))
        
        # Make the call via RingCentral
        call_model = self.env['ringcentral.call']
        
        try:
            result = call_model.action_make_call(cleaned_number)
            
            return {
                'dialed_number': cleaned_number,
                'call_id': result.get('id'),
                'ringout_id': result.get('ringout_id'),
            }
        except Exception as e:
            raise UserError(_("RingCentral call failed: %s") % str(e))
    
    @api.model
    def _normalize_phone_number(self, phone_number, country_code=None):
        """
        Normalize phone number to E.164 format for RingCentral API.
        
        :param phone_number: Raw phone number string
        :param country_code: Default country code (e.g., 'US', 'GB')
        :return: Normalized phone number in E.164 format (+1234567890)
        """
        return normalize_phone(phone_number, country_code)
    
    @api.model
    def _clean_phone_number(self, phone_number):
        """Alias for backward compatibility"""
        return self._normalize_phone_number(phone_number)
    
    @api.model
    def format_phone_display(self, phone_number, format_type='national'):
        """
        Format phone number for display.
        
        :param phone_number: Phone number string
        :param format_type: 'national', 'international', or 'e164'
        :return: Formatted phone number
        """
        return format_phone_for_display(phone_number, format_type)
    
    @api.model
    def find_partner_by_phone(self, phone_number, limit=1):
        """
        Find partner(s) by phone number with fuzzy matching.
        
        Uses the last 10 digits for matching to handle different formats.
        
        :param phone_number: Phone number to search
        :param limit: Maximum results to return
        :return: res.partner recordset
        """
        if not phone_number:
            return self.env['res.partner']
        
        # Get searchable digits (last 10)
        digits = ''.join(c for c in phone_number if c.isdigit())
        if len(digits) < 7:
            return self.env['res.partner']
        
        search_digits = digits[-10:]
        
        return self.env['res.partner'].search([
            '|',
            ('phone', 'ilike', search_digits),
            ('mobile', 'ilike', search_digits),
        ], limit=limit)


# ===========================
# Standalone Utility Functions
# ===========================

@lru_cache(maxsize=10000)
def normalize_phone(phone_number, country_code=None):
    """
    Normalize phone number to E.164 format.
    
    Uses caching for performance on repeated normalizations.
    
    :param phone_number: Raw phone number string
    :param country_code: Default country code (e.g., 'US', 'GB')
    :return: Normalized phone number in E.164 format (+1234567890)
    """
    if not phone_number:
        return None
    
    # Remove all non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', str(phone_number))
    
    if not cleaned:
        return None
    
    # Already in E.164 format
    if cleaned.startswith('+'):
        # Validate length
        if len(cleaned) >= 10 and len(cleaned) <= 16:
            return cleaned
        return None
    
    # Remove leading zeros (international dialing prefix)
    cleaned = cleaned.lstrip('0')
    
    if not cleaned:
        return None
    
    # Country-specific handling
    country_code = (country_code or 'US').upper()
    
    if country_code == 'US':
        # US numbers
        if len(cleaned) == 10:
            return f'+1{cleaned}'
        elif len(cleaned) == 11 and cleaned.startswith('1'):
            return f'+{cleaned}'
    elif country_code == 'GB':
        # UK numbers
        if len(cleaned) == 10 and cleaned.startswith('7'):
            return f'+44{cleaned}'
        elif len(cleaned) == 11 and cleaned.startswith('0'):
            return f'+44{cleaned[1:]}'
    elif country_code in ('DE', 'FR', 'IT', 'ES'):
        # European countries
        if len(cleaned) >= 9 and len(cleaned) <= 12:
            country_dial_codes = {'DE': '49', 'FR': '33', 'IT': '39', 'ES': '34'}
            dial_code = country_dial_codes.get(country_code, '')
            if not cleaned.startswith(dial_code):
                return f'+{dial_code}{cleaned}'
            return f'+{cleaned}'
    
    # Default: assume it's complete with country code if 11+ digits
    if len(cleaned) >= 11:
        return f'+{cleaned}'
    elif len(cleaned) == 10:
        # Assume US by default
        return f'+1{cleaned}'
    
    return None


def format_phone_for_display(phone_number, format_type='national'):
    """
    Format phone number for human-readable display.
    
    :param phone_number: Phone number string (preferably E.164)
    :param format_type: 'national', 'international', or 'e164'
    :return: Formatted phone number
    """
    if not phone_number:
        return ''
    
    # Normalize first
    normalized = normalize_phone(phone_number)
    if not normalized:
        return phone_number  # Return original if can't normalize
    
    if format_type == 'e164':
        return normalized
    
    # Remove + for formatting
    digits = normalized[1:] if normalized.startswith('+') else normalized
    
    # US formatting
    if digits.startswith('1') and len(digits) == 11:
        area = digits[1:4]
        prefix = digits[4:7]
        line = digits[7:11]
        
        if format_type == 'national':
            return f'({area}) {prefix}-{line}'
        else:  # international
            return f'+1 ({area}) {prefix}-{line}'
    
    # UK formatting
    if digits.startswith('44') and len(digits) >= 11:
        rest = digits[2:]
        if format_type == 'national':
            return f'0{rest[:4]} {rest[4:]}'
        else:
            return f'+44 {rest[:4]} {rest[4:]}'
    
    # Default international format
    if format_type == 'national':
        return digits
    else:
        return f'+{digits}'


def extract_phone_digits(phone_number, min_length=7):
    """
    Extract just the digits from a phone number.
    
    :param phone_number: Phone number string
    :param min_length: Minimum digits required
    :return: String of digits or None
    """
    if not phone_number:
        return None
    
    digits = ''.join(c for c in str(phone_number) if c.isdigit())
    
    if len(digits) >= min_length:
        return digits
    return None
