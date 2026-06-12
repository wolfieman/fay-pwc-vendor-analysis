"""VendorScope database layer: SQLite + sqlite-vec.

The relational schema and the embedding vectors live in one SQLite file. This
package owns the connection helpers (:mod:`~vendorscope.db.connection`) and the
schema DDL (:mod:`~vendorscope.db.schema`).

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

from .connection import build, connect
from .schema import EMBED_DIM, SCHEMA_SQL, create_schema

__all__ = ["EMBED_DIM", "SCHEMA_SQL", "build", "connect", "create_schema"]
