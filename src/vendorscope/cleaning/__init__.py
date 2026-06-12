"""The cleaning core: pure normalizers, audit records, and the role engine.

Everything here is a pure function or a frozen value object: no IO, no globals,
no wall-clock. The imperative shell (``evp_client``, ``cli``) drives it.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""
