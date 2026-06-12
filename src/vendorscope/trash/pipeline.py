"""VendorScope pipeline orchestrator.

A thin entry point that runs the acquisition and cleaning scripts in sequence.
It adds no analysis logic of its own: each subcommand shells out to the existing
script with the same arguments the README documents. "reproduce" runs the full
clean, profile, and audit chain over the anonymized sample, with no scraping.

Usage:
    python -m vendorscope.pipeline reproduce
    python -m vendorscope.pipeline clean --input data/sample/vendor-details-evp-nc.csv
    python -m vendorscope.pipeline acquire-licenses ...   # opt-in; network

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "data" / "sample"
PROCESSED = ROOT / "data" / "processed"

# Subcommand -> the script it forwards to. acquire-* hit the network / a browser
# and are never run by "reproduce"; they are invoked explicitly and opt-in.
_ACQ = ROOT / "src" / "acquisition"
_CLEAN = ROOT / "src" / "cleaning"
SCRIPTS = {
    "acquire-licenses": _ACQ / "nclbgc_licenses_acquisition.py",
    "acquire-details": _ACQ / "nclbgc_license_details_acquisition.py",
    "clean": _CLEAN / "clean_data.py",
    "profile": _CLEAN / "profile_data.py",
    "audit": _CLEAN / "make_audit.py",
}


def _run(script: Path, args: list[str]) -> None:
    """Run a pipeline script in a subprocess, raising on a non-zero exit."""
    subprocess.run([sys.executable, str(script), *args], check=True)


def reproduce() -> None:
    """Run clean, profile, then audit over data/sample (no scraping)."""
    vendor = SAMPLE / "vendor-details-evp-nc.csv"
    licenses = SAMPLE / "nclbgc-license-details.csv"
    _run(SCRIPTS["clean"], ["--input", str(vendor), "--outdir", str(PROCESSED)])
    _run(
        SCRIPTS["profile"],
        ["--files", str(vendor), str(licenses), "--outdir", str(PROCESSED)],
    )
    _run(
        SCRIPTS["audit"],
        [
            "--summary",
            str(PROCESSED / "pwc-profile-summary.csv"),
            "--out",
            str(PROCESSED / "data_audit.md"),
        ],
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="vendorscope.pipeline", description="VendorScope pipeline orchestrator."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser(
        "reproduce", help="Run clean, profile, and audit over the sample (no scraping)."
    )
    for name in SCRIPTS:
        p = sub.add_parser(
            name, help=f"Run the {name} script (forwards remaining args)."
        )
        p.add_argument(
            "args", nargs=argparse.REMAINDER, help="Arguments forwarded to the script."
        )
    ns = parser.parse_args(argv)
    if ns.command == "reproduce":
        reproduce()
    else:
        _run(SCRIPTS[ns.command], ns.args)


if __name__ == "__main__":
    main()
