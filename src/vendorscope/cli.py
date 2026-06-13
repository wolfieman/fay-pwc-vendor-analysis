"""The orchestration shell: ``acquire-evp``, ``profile``, ``clean`` subcommands.

The only entrypoint that wires the pure core to the filesystem and the network.
Each subcommand is thin: it resolves paths, calls the core, and writes artifacts.
Run reports written here are values-free (counts by column and rule); the
PII-bearing audit records go only to the gitignored audit zone.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

from . import (
    evp_client,
    evp_parse,
    http_client,
    nclbgc_client,
    paths,
    profiling,
    tabular,
)
from .cleaning import config, engine

_VOCAB_COLUMNS = tuple(
    col
    for col, rule in config.VENDOR_CONFIG.columns.items()
    if rule.role in ("vocab", "flag")
)
_RED_SNAKE = tuple(config.SNAKE_CASE[c] for c in config.RED_COLUMNS)
_LICENSE_RED_SNAKE = tuple(
    config.LICENSE_SNAKE_CASE[c] for c in config.LICENSE_RED_COLUMNS
)


def _run_id(source: str) -> str:
    return time.strftime("%Y%m%dT%H%M%S") + f"-{source}"


def _acquire_evp(args: argparse.Namespace, *, transport, data_raw: Path) -> int:
    client = http_client.build_client(transport=transport)
    try:
        result = evp_client.acquire(
            client=client, data_raw=data_raw, run_id=_run_id("evp"), floor=args.floor
        )
    except evp_client.DriftHalt as halt:
        print(f"HALT: {halt}", file=sys.stderr)
        return 2
    except (evp_parse.EmbeddedDataError, tabular.ManifestError) as exc:
        print(f"HALT: shape change — {exc}; see {evp_client.RUNBOOK}", file=sys.stderr)
        return 3
    finally:
        client.close()
    print(f"acquired {result.record_count} records -> {result.raw_dir}")
    return 0


def _load_run(data_raw: Path, run_id: str) -> list[dict[str, str]]:
    page = (data_raw / "evp" / run_id / "vendordetails-page-1.html").read_text(
        encoding="utf-8"
    )
    return evp_parse.parse_records(page)


def _profile(args: argparse.Namespace, *, data_raw: Path, data_processed: Path) -> int:
    records = _load_run(data_raw, args.run_id)
    report = profiling.profile(
        records, vocab_columns=_VOCAB_COLUMNS, red_columns=config.RED_COLUMNS
    )
    out_dir = data_processed / "profile"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"evp-vendor-master-profile-{args.run_id[:8]}.json"
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"profiled {report['record_count']} records -> {out}")
    return 0


def _counts(pairs) -> dict[str, int]:
    return {f"{col}:{rule}": n for (col, rule), n in Counter(pairs).most_common()}


def _clean_table(
    records: list[dict[str, str]],
    *,
    run_id: str,
    data_processed: Path,
    table_config: config.TableConfig,
    snake_case: dict[str, str],
    red_snake: tuple[str, ...],
    expected_columns: tuple[str, ...],
    master_name: str,
    contacts_name: str,
    noun: str,
) -> int:
    """The clean pipeline shared by every source: manifest check, clean, conserve,
    snake_case rename, PII split, deliverable pair, and a values-free run report.

    ``master_name``/``contacts_name`` carry a ``{date}`` placeholder; ``noun`` is the
    record word printed (rows, licenses). Source-specific decoding happens upstream.
    """
    if records:
        tabular.assert_manifest(records[0].keys(), expected=expected_columns)
    rows = engine.assign_row_keys(records)
    result = engine.clean_table(rows, table_config)
    if len(rows) != len(result.rows) + len(result.drops):
        print("HALT: row conservation identity violated", file=sys.stderr)
        return 4

    renamed = tabular.rename_snake(result.rows, snake_case)
    deliverable, contacts = tabular.split_pii(renamed, red_snake)
    date = run_id[:8]
    deliverable_cols = [
        "row_key",
        *(c for c in snake_case.values() if c not in red_snake),
    ]
    data_processed.mkdir(parents=True, exist_ok=True)
    tabular.write_csv(
        data_processed / master_name.format(date=date),
        deliverable,
        columns=deliverable_cols,
    )
    tabular.write_csv(
        data_processed / contacts_name.format(date=date),
        contacts,
        columns=["row_key", *red_snake],
    )

    audit_dir = data_processed / "audit" / run_id
    audit_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "run_id": run_id,
        "rows_in": len(rows),
        "rows_out": len(result.rows),
        "dedup_drops": len(result.drops),
        "corrections": len(result.corrections),
        "violations": len(result.violations),
        "corrections_by_rule": _counts((c.column, c.rule) for c in result.corrections),
        "violations_by_rule": _counts((v.column, v.rule) for v in result.violations),
    }
    (audit_dir / "run-report.json").write_text(
        json.dumps(report, indent=1), encoding="utf-8"
    )
    print(
        f"cleaned {report['rows_in']} -> {report['rows_out']} {noun} "
        f"({report['corrections']} corrections, {report['violations']} violations, "
        f"{report['dedup_drops']} drops)"
    )
    return 0


def _clean(args: argparse.Namespace, *, data_raw: Path, data_processed: Path) -> int:
    return _clean_table(
        _load_run(data_raw, args.run_id),
        run_id=args.run_id,
        data_processed=data_processed,
        table_config=config.VENDOR_CONFIG,
        snake_case=config.SNAKE_CASE,
        red_snake=_RED_SNAKE,
        expected_columns=config.EXPECTED_COLUMNS,
        master_name="evp-vendor-master-vendor-{date}.csv",
        contacts_name="evp-vendor-contacts-vendor-{date}.csv",
        noun="rows",
    )


def _slice1_vendors(data_processed: Path) -> list[dict[str, str]]:
    """Read the slice-1 deliverable for the (name, GC license number) driver list."""
    masters = sorted(data_processed.glob("evp-vendor-master-vendor-*.csv"))
    if not masters:
        raise FileNotFoundError("no slice-1 eVP deliverable to drive the NCLBGC lookup")
    rows = tabular.read_csv(masters[-1])
    return [
        {"name": r["name"], "license_number": r["general_contractor_license_number"]}
        for r in rows
    ]


def _acquire_nclbgc(
    args: argparse.Namespace, *, transport, data_raw: Path, data_processed: Path
) -> int:
    try:
        vendors = _slice1_vendors(data_processed)
    except FileNotFoundError as exc:
        print(f"HALT: {exc}", file=sys.stderr)
        return 5
    if args.limit:
        vendors = vendors[: args.limit]
    client = http_client.build_client(transport=transport)
    try:
        result = nclbgc_client.acquire(
            client=client, data_raw=data_raw, run_id=_run_id("nclbgc"), vendors=vendors
        )
    finally:
        client.close()
    matched = sum(1 for r in result.resolutions if r.status != "unresolved")
    print(
        f"resolved {matched} of {len(vendors)} vendors "
        f"({result.record_count} licenses) -> {result.raw_dir}"
    )
    return 0


def _load_nclbgc_run(data_raw: Path, run_id: str) -> list[dict[str, str]]:
    path = data_raw / "nclbgc" / run_id / "nclbgc-licenses.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _clean_nclbgc(
    args: argparse.Namespace, *, data_raw: Path, data_processed: Path
) -> int:
    return _clean_table(
        _load_nclbgc_run(data_raw, args.run_id),
        run_id=args.run_id,
        data_processed=data_processed,
        table_config=config.LICENSE_CONFIG,
        snake_case=config.LICENSE_SNAKE_CASE,
        red_snake=_LICENSE_RED_SNAKE,
        expected_columns=config.LICENSE_EXPECTED_COLUMNS,
        master_name="nclbgc-license-master-{date}.csv",
        contacts_name="nclbgc-license-contacts-{date}.csv",
        noun="licenses",
    )


def run(
    argv: list[str] | None = None,
    *,
    transport=None,
    data_raw: Path | None = None,
    data_processed: Path | None = None,
) -> int:
    """Parse args and dispatch; ``transport``/``data_raw`` are test injection seams."""
    data_raw = data_raw or paths.DATA_RAW
    data_processed = data_processed or paths.DATA_PROCESSED

    parser = argparse.ArgumentParser(prog="vendorscope")
    sub = parser.add_subparsers(dest="command", required=True)
    acq = sub.add_parser("acquire-evp", help="fetch and freeze the eVP results page")
    acq.add_argument("--floor", type=int, default=config.RECORD_FLOOR)
    prof = sub.add_parser("profile", help="profile a frozen raw run (values-free)")
    prof.add_argument("--run-id", required=True)
    cln = sub.add_parser("clean", help="clean a frozen raw run into the processed pair")
    cln.add_argument("--run-id", required=True)
    acqn = sub.add_parser(
        "acquire-nclbgc", help="resolve and enrich slice-1 licenses against NCLBGC"
    )
    acqn.add_argument("--limit", type=int, default=0, help="cap the vendor count")
    clnn = sub.add_parser(
        "clean-nclbgc", help="clean a frozen NCLBGC run into the license pair"
    )
    clnn.add_argument("--run-id", required=True)

    args = parser.parse_args(argv)
    if args.command == "acquire-evp":
        return _acquire_evp(args, transport=transport, data_raw=data_raw)
    if args.command == "profile":
        return _profile(args, data_raw=data_raw, data_processed=data_processed)
    if args.command == "clean":
        return _clean(args, data_raw=data_raw, data_processed=data_processed)
    if args.command == "acquire-nclbgc":
        return _acquire_nclbgc(
            args, transport=transport, data_raw=data_raw, data_processed=data_processed
        )
    return _clean_nclbgc(args, data_raw=data_raw, data_processed=data_processed)


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
