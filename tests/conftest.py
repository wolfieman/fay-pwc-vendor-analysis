"""Test-session bootstrap: tests are offline by default.

``TEST_MODE`` defaults on via ``setdefault`` so a deliberate shell override
(``TEST_MODE=false``) still enables the opt-in live integration tests.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import os

os.environ.setdefault("TEST_MODE", "true")
