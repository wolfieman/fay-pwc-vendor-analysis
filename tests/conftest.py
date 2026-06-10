"""Pytest configuration: default unit runs to offline TEST_MODE so nothing
reaches the network unless a test explicitly opts in.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import os

os.environ.setdefault("TEST_MODE", "true")
