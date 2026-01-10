# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class IVRMenu(models.Model):
    _name = 'ringcentral.ivr.menu'
    _description = 'IVR Menu'
    _order = 'name'
    _parent_store = True

    name = fields.Char(string='Menu Name', required=True)
    active = fields.Boolean(string='Active', default=True)
    
    # RingCentral Reference
    ringcentral_ivr_id = fields.Char(string='RingCentral IVR ID')
    
    # Hierarchy
    parent_id = fields.Many2one(
        'ringcentral.ivr.menu',
        string='Parent Menu',
        index=True,
    )
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many(
        'ringcentral.ivr.menu',
        'parent_id',
        string='Sub-Menus',
    )
    
    # Prompt
    prompt_type = fields.Selection([
        ('tts', 'Text-to-Speech'),
        ('audio', 'Audio File'),
    ], string='Prompt Type', default='tts')
    prompt_text = fields.Text(string='Prompt Text')
    prompt_audio = fields.Binary(string='Prompt Audio')
    prompt_audio_filename = fields.Char(string='Audio Filename')
    
    # Options
    option_ids = fields.One2many(
        'ringcentral.ivr.menu.option',
        'menu_id',
        string='Menu Options',
    )
    
    # Default action (timeout/no input)
    default_action = fields.Selection([
        ('repeat', 'Repeat Menu'),
        ('transfer', 'Transfer'),
        ('voicemail', 'Voicemail'),
        ('disconnect', 'Disconnect'),
    ], string='Default Action', default='repeat')
    default_extension = fields.Char(string='Default Extension')
    
    # Settings
    timeout = fields.Integer(
        string='Input Timeout (sec)',
        default=5,
    )
    max_attempts = fields.Integer(
        string='Max Attempts',
        default=3,
    )

    def action_preview(self):
        """Preview IVR flow"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('IVR Preview'),
            'res_model': 'ringcentral.ivr.menu',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_sync_to_ringcentral(self):
        """Sync IVR to RingCentral"""
        self.ensure_one()
        
        api = self.env['ringcentral.api'].get_api()
        if not api:
            return
        
        try:
            # Build IVR config and push to RingCentral
            ivr_config = self._build_ivr_config()
            # api.update_ivr(self.ringcentral_ivr_id, ivr_config)
            _logger.info(f'Synced IVR: {self.name}')
        except Exception as e:
            _logger.error(f'Failed to sync IVR: {e}')

    def _build_ivr_config(self):
        """Build IVR configuration for RingCentral API"""
        self.ensure_one()
        
        config = {
            'name': self.name,
            'prompt': self.prompt_text if self.prompt_type == 'tts' else None,
            'actions': [],
        }
        
        for option in self.option_ids:
            config['actions'].append({
                'input': option.key,
                'action': option.action,
                'extension': option.extension,
            })
        
        return config


class IVRMenuOption(models.Model):
    _name = 'ringcentral.ivr.menu.option'
    _description = 'IVR Menu Option'
    _order = 'key'

    menu_id = fields.Many2one(
        'ringcentral.ivr.menu',
        string='Menu',
        required=True,
        ondelete='cascade',
    )
    
    key = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
        ('6', '6'),
        ('7', '7'),
        ('8', '8'),
        ('9', '9'),
        ('0', '0'),
        ('*', '*'),
        ('#', '#'),
    ], string='Key', required=True)
    
    description = fields.Char(string='Description')
    
    action = fields.Selection([
        ('transfer_ext', 'Transfer to Extension'),
        ('transfer_queue', 'Transfer to Queue'),
        ('submenu', 'Go to Submenu'),
        ('voicemail', 'Voicemail'),
        ('dial_by_name', 'Dial by Name'),
        ('repeat', 'Repeat Menu'),
        ('disconnect', 'Disconnect'),
    ], string='Action', required=True)
    
    # Action targets
    extension = fields.Char(string='Extension')
    queue_id = fields.Many2one(
        'ringcentral.call.queue',
        string='Queue',
    )
    submenu_id = fields.Many2one(
        'ringcentral.ivr.menu',
        string='Submenu',
    )
