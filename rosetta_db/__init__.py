"""
Rosetta DB - Versioned translation database for Battle Brothers mods.

Extends existing translations.db with version tracking tables.
"""

from .database import Database, compute_string_id

__all__ = ['Database', 'compute_string_id']
