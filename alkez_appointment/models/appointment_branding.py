# Copyright 2024 Your Company
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class AppointmentBranding(models.Model):
    """Custom branding settings for appointment pages"""
    _name = "appointment.branding"
    _description = "Appointment Branding"
    _rec_name = "user_id"

    user_id = fields.Many2one(
        'res.users',
        string="User",
        required=True,
        ondelete='cascade',
        default=lambda self: self.env.user
    )
    
    # Company/Personal Branding
    company_name = fields.Char(
        string="Display Name",
        help="Name shown on booking pages (defaults to user name)"
    )
    tagline = fields.Char(
        string="Tagline",
        help="Short description shown under the name"
    )
    
    # Logo
    logo = fields.Binary(string="Logo", attachment=True)
    logo_filename = fields.Char(string="Logo Filename")
    
    # Colors
    primary_color = fields.Char(
        string="Primary Color",
        default="#0069ff",
        help="Main brand color"
    )
    secondary_color = fields.Char(
        string="Secondary Color",
        default="#004ba0",
        help="Secondary/accent color"
    )
    text_color = fields.Char(
        string="Text Color",
        default="#1a1a1a",
        help="Primary text color"
    )
    background_color = fields.Char(
        string="Background Color",
        default="#ffffff",
        help="Page background color"
    )
    
    # Fonts
    font_family = fields.Selection([
        ('inter', 'Inter (Modern)'),
        ('roboto', 'Roboto'),
        ('open_sans', 'Open Sans'),
        ('lato', 'Lato'),
        ('poppins', 'Poppins'),
        ('montserrat', 'Montserrat'),
        ('system', 'System Default'),
    ], string="Font", default='inter')
    
    # Custom CSS
    custom_css = fields.Text(
        string="Custom CSS",
        help="Advanced: Add custom CSS styles"
    )
    
    # Header/Footer
    show_powered_by = fields.Boolean(
        string="Show 'Powered by' Footer",
        default=True
    )
    custom_footer = fields.Html(
        string="Custom Footer",
        help="Custom HTML for footer area"
    )
    
    # Background Image
    background_image = fields.Binary(
        string="Background Image",
        attachment=True
    )
    background_image_filename = fields.Char()
    background_style = fields.Selection([
        ('none', 'None'),
        ('cover', 'Cover'),
        ('tile', 'Tile'),
        ('fixed', 'Fixed'),
    ], string="Background Style", default='none')
    
    # Social Links
    website_url = fields.Char(string="Website")
    linkedin_url = fields.Char(string="LinkedIn")
    twitter_url = fields.Char(string="Twitter/X")
    facebook_url = fields.Char(string="Facebook")
    instagram_url = fields.Char(string="Instagram")
    
    # Privacy & Terms
    privacy_url = fields.Char(string="Privacy Policy URL")
    terms_url = fields.Char(string="Terms of Service URL")
    
    # Banner/Announcement
    show_banner = fields.Boolean(string="Show Banner", default=False)
    banner_text = fields.Char(string="Banner Text")
    banner_color = fields.Char(string="Banner Color", default="#fef3c7")
    banner_text_color = fields.Char(string="Banner Text Color", default="#92400e")

    _sql_constraints = [
        ('user_unique', 'unique(user_id)', 'Each user can only have one branding configuration!')
    ]

    def get_css_variables(self):
        """Generate CSS custom properties for branding"""
        self.ensure_one()
        return f"""
        :root {{
            --appointment-primary: {self.primary_color or '#0069ff'};
            --appointment-secondary: {self.secondary_color or '#004ba0'};
            --appointment-text: {self.text_color or '#1a1a1a'};
            --appointment-bg: {self.background_color or '#ffffff'};
            --appointment-font: {self._get_font_stack()};
        }}
        """

    def _get_font_stack(self):
        fonts = {
            'inter': "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
            'roboto': "'Roboto', Arial, sans-serif",
            'open_sans': "'Open Sans', Arial, sans-serif",
            'lato': "'Lato', Arial, sans-serif",
            'poppins': "'Poppins', Arial, sans-serif",
            'montserrat': "'Montserrat', Arial, sans-serif",
            'system': "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        }
        return fonts.get(self.font_family, fonts['system'])

    @api.model
    def get_branding_for_user(self, user_id):
        """Get or create branding for a user"""
        branding = self.search([('user_id', '=', user_id)], limit=1)
        if not branding:
            branding = self.create({'user_id': user_id})
        return branding
