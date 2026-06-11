"""VendorScope cleaning engine: source-agnostic value cleaning with a
report-don't-coerce contract and structured corrections/violations.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

from .config import (
    CROSS_VALIDATION_CONFIG,
    LICENSE_CONFIG,
    VENDOR_CONFIG,
    CrossValidationConfig,
    TableConfig,
)
from .pipeline import (
    CleanResult,
    clean_table,
    corrections_frame,
    cross_validate,
    violations_frame,
)
from .transforms import Correction, Violation, split_pii

__all__ = [
    "CROSS_VALIDATION_CONFIG",
    "LICENSE_CONFIG",
    "VENDOR_CONFIG",
    "CleanResult",
    "Correction",
    "CrossValidationConfig",
    "TableConfig",
    "Violation",
    "clean_table",
    "corrections_frame",
    "cross_validate",
    "split_pii",
    "violations_frame",
]
