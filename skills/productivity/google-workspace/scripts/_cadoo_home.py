"""Resolve CADOO_HOME for standalone skill scripts.

Skill scripts may run outside the Cadoo process (e.g. system Python,
nix env, CI) where ``cadoo_constants`` is not importable.  This module
provides the same ``get_cadoo_home()`` and ``display_cadoo_home()``
contracts as ``cadoo_constants`` without requiring it on ``sys.path``.

When ``cadoo_constants`` IS available it is used directly so that any
future enhancements (profile resolution, Docker detection, etc.) are
picked up automatically.  The fallback path replicates the core logic
from ``cadoo_constants.py`` using only the stdlib.

All scripts under ``google-workspace/scripts/`` should import from here
instead of duplicating the ``CADOO_HOME = Path(os.getenv(...))`` pattern.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from cadoo_constants import display_cadoo_home as display_cadoo_home
    from cadoo_constants import get_cadoo_home as get_cadoo_home
except (ModuleNotFoundError, ImportError):

    def get_cadoo_home() -> Path:
        """Return the Cadoo home directory (default: ~/.cadoo).

        Mirrors ``cadoo_constants.get_cadoo_home()``."""
        val = os.environ.get("CADOO_HOME", "").strip()
        return Path(val) if val else Path.home() / ".cadoo"

    def display_cadoo_home() -> str:
        """Return a user-friendly ``~/``-shortened display string.

        Mirrors ``cadoo_constants.display_cadoo_home()``."""
        home = get_cadoo_home()
        try:
            return "~/" + str(home.relative_to(Path.home()))
        except ValueError:
            return str(home)
