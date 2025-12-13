# -*- coding: utf-8 -*-
from . import models
from . import controllers
from . import hooks

# Export hook functions to package namespace so Odoo can call them by name
try:
    from .hooks import post_init_hook, uninstall_hook
except Exception:
    # keep running even if hooks aren't importable during static analysis
    post_init_hook = None
    uninstall_hook = None

def pre_init_hook(cr):
    # placeholder for any pre-init logic
    return True
