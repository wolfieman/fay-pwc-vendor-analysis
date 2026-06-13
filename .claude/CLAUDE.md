# Claude Code Instructions — VendorScope

## This is a PUBLIC repository

Keep everything publishable. **Never** commit private context: no references to
other private repositories, course names, advisor/teammate names, secrets, API
keys, or absolute filesystem paths. Treat every commit and file as world-readable.

## Commits

A dependency-free `commit-msg` guard is installed in `.git/hooks/` and blocks AI
attribution and absolute filesystem paths. Write imperative subjects; keep messages
free of attribution, secrets, and private references.

## Shell

Use git bash, not PowerShell on this machine (a PreToolUse hook enforces it).

## Releases and versioning

Milestone tags only, one per completed slice (D7). When bumping the version, sync
all three sources in one commit — `pyproject.toml`, `src/vendorscope/__init__.py`,
`CITATION.cff` (and its `date-released`) — **and run `uv lock`** so `uv.lock`
records the new project version. CI runs `uv sync --locked`, which fails if the
lock is stale; a version bump without re-locking turns main red. After any push,
confirm the run is green (`gh run list --branch main`) before moving on.
