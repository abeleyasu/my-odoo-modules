# -*- coding: utf-8 -*-
# Copyright 2025 Odoo Community
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

# Core Models
from . import office_document_new  # Enhanced document with all file types
from . import office_folder_new    # Enhanced folder with sharing and colors

# Access Control & Sharing
from . import office_access        # Individual access & share links

# Version History & Activity
from . import office_version       # Versions, comments, activity log

# Legacy models (deprecated - kept for migration compatibility)
# from . import office_document
# from . import office_folder
