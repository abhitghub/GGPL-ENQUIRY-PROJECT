"""Pytest setup for the API test suite.

The tests authenticate via X-Org-Id / X-User-Id headers rather than real
session cookies, so they run with login enforcement disabled (header-based
identity fallback). This must be set before the app imports its settings.
"""

import os

os.environ.setdefault("LOGIN_ENABLED", "false")
