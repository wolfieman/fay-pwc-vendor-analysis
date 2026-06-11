"""Connection helpers for the VendorScope SQLite + sqlite-vec database.

Every connection must load the ``sqlite-vec`` extension (so ``vec0`` virtual
tables work) and enable foreign-key enforcement (SQLite defaults it off, so the
schema's referential constraints are inert without it).

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import sqlite3

import sqlite_vec

from .schema import create_schema


def connect(path: str = ":memory:") -> sqlite3.Connection:
    """Open a connection with ``sqlite-vec`` loaded and foreign keys enforced."""
    conn = sqlite3.connect(path)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def build(path: str = ":memory:") -> sqlite3.Connection:
    """Open a connection and apply the full schema. Returns the live connection."""
    conn = connect(path)
    create_schema(conn)
    return conn
