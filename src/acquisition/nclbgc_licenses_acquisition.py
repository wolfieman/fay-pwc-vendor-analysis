#!/usr/bin/env python3
"""
nclbgc_licenses_acquisition.py — Look up NCLBGC license account numbers by company
name (Playwright) and fill them into a spreadsheet column. Writes 'L.xxxxx', 'PENDING',
or 'NA' per row. Supports normalized-name retries and parallel page reuse.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""
import pandas.api.types as ptypes
import argparse
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd
from tqdm import tqdm
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

from vendorscope.columns import get_col_indices
from vendorscope.text import normalize_name

SEARCH_URL = "https://portal.nclbgc.org/Public/Search"

# ---------- DataFrame helpers ----------


def save_xlsx(df: pd.DataFrame, out_path: Path):
    """Write Excel; if locked, write timestamped alternative."""
    try:
        with pd.ExcelWriter(out_path, engine="openpyxl", mode="w") as xw:
            df.to_excel(xw, index=False)
        print(f"✅ Done. Wrote: {out_path}")
    except PermissionError:
        alt = out_path.with_name(
            out_path.stem + f".{datetime.now():%Y%m%d-%H%M%S}.xlsx")
        with pd.ExcelWriter(alt, engine="openpyxl", mode="w") as xw:
            df.to_excel(xw, index=False)
        print(f"⚠️ File in use: {out_path}\n   ➜ Wrote instead: {alt}")

# ---------- Playwright helpers ----------


def goto_search(page):
    page.context.set_default_timeout(10000)
    page.goto(SEARCH_URL, wait_until="domcontentloaded")
    # Try to close cookie banner if present
    try:
        page.get_by_role("button", name=re.compile(
            "accept|agree|ok", re.I)).click(timeout=3000)
    except Exception:
        pass


def click_search(page):
    for locator in [
        "button:has-text('Search')",
        "input[type=submit][value='Search']",
        "form button[type=submit]",
    ]:
        try:
            page.locator(locator).click(timeout=4000)
            return
        except Exception:
            continue
    page.get_by_role("button", name="Search").click()


def header_index(page, text: str) -> int:
    ths = page.locator("table thead th")
    n = ths.count()
    t = text.lower()
    for i in range(n):
        try:
            if t in ths.nth(i).inner_text().strip().lower():
                return i
        except Exception:
            pass
    return -1


def extract_row_account_text(row_locator) -> str:
    """Return the link text in a row if present, else first cell text."""
    try:
        link = row_locator.locator("a").first
        if link.count() > 0:
            txt = link.inner_text().strip()
            if txt:
                return txt
    except Exception:
        pass
    try:
        return row_locator.locator("td").first.inner_text().strip()
    except Exception:
        return ""


def classify_accounts(page, company_name: str) -> Tuple[Optional[str], bool]:
    """
    Return (non_pending_license_text_or_None, pending_present_flag).
    - If one or more non-pending accounts exist, return the first (e.g., 'L.27348'), pending flag may be True/False.
    - If only pending exists, return None and pending_present=True.
    - If no rows at all, return (None, False).
    """
    rows = page.locator("table tbody tr")
    n = rows.count()
    if n == 0:
        return None, False

    owner_idx = header_index(page, "owner")
    q = (company_name or "").strip().lower()

    non_pending: Optional[str] = None
    pending_present = False

    # Prefer matching owner row first; otherwise evaluate all
    candidate_indexes = list(range(n))
    if owner_idx >= 0 and q:
        for i in range(n):
            try:
                cell_txt = rows.nth(i).locator(
                    f"td:nth-child({owner_idx+1})").inner_text().lower()
                if q in cell_txt:
                    candidate_indexes = [
                        i] + [idx for idx in candidate_indexes if idx != i]
                    break
            except Exception:
                pass

    for i in candidate_indexes:
        row = rows.nth(i)
        txt = extract_row_account_text(row)
        if not txt:
            continue
        if "pending" in txt.lower():
            pending_present = True
            continue
        # Found a real license (e.g., L.27348)
        non_pending = txt
        break

    return non_pending, pending_present


def fill_for_name(page, name: str, delay_after=0.7, try_normalized=False, reuse=False) -> str:
    """
    Perform a single search and return:
      - 'L.xxxxx' (preferred if exists),
      - 'PENDING' (if only pending rows),
      - 'NA' (if no results).

    If reuse=True, we assume the search page is already open
    and just clear + retype the query, then click Search again.
    """
    queries = [name]
    if try_normalized:
        norm = normalize_name(name)
        if norm and norm.lower() != (name or "").lower():
            queries.append(norm)

    for q in queries:
        # Only load the page when *not* reusing
        if not reuse:
            goto_search(page)

        # Fill Company Name input using multiple selectors
        filled = False
        for sel in [
            "input[placeholder='Company Name']",
            "input#CompanyName",
            "input[name='CompanyName']",
            "xpath=//label[contains(.,'Company Name')]/following::input[1]",
        ]:
            try:
                el = page.locator(sel)
                # clear any existing value then type the new query
                el.fill("", timeout=1500)
                el.fill(q, timeout=4000)
                filled = True
                break
            except Exception:
                continue
        if not filled:
            # last resort: first text input inside a form
            inputs = page.locator("form input[type='text'], form input")
            for i in range(min(inputs.count(), 6)):
                try:
                    el = inputs.nth(i)
                    # prefer an empty field (the Company Name box is usually empty between searches)
                    if not el.input_value():
                        el.fill(q, timeout=2000)
                        filled = True
                        break
                except Exception:
                    pass
        if not filled:
            continue

        click_search(page)
        time.sleep(delay_after)

        # Wait for rows or a clear "0 entries" message
        try:
            page.wait_for_selector("table tbody tr", timeout=8000)
        except PWTimeout:
            txt = page.content().lower()
            if "showing 0 to 0 of 0 entries" in txt:
                # try next query variant if any
                continue
            return "NA"

        non_pending, pending_present = classify_accounts(page, q)
        if non_pending:
            return non_pending
        if pending_present:
            return "PENDING"

    return "NA"


# ---------- Main ----------


def main():
    ap = argparse.ArgumentParser(
        description="Fill NCLBGC license numbers (Account #) into Excel Column B.")
    ap.add_argument("--input", required=True,
                    help="Path to Excel file (.xlsx)")
    ap.add_argument("--sheet", default=None,
                    help="Worksheet name (default: first sheet)")
    ap.add_argument("--name-col", default="A",
                    help="Company name column (letter or header). Default: A")
    ap.add_argument("--license-col", default="B",
                    help="License number column (letter or header). Default: B")
    ap.add_argument("--overwrite", action="store_true",
                    help="Overwrite existing values in license column")
    ap.add_argument("--headful", action="store_true",
                    help="Show browser window (for debugging)")
    ap.add_argument("--pause", type=float, default=0.7,
                    help="Delay between searches (seconds)")
    ap.add_argument("--limit", type=int, default=None,
                    help="Process only first N rows (testing)")
    ap.add_argument("--start-row", type=int, default=None,
                    help="First Excel row to process (1-based; data starts at row 2)")
    ap.add_argument("--end-row", type=int, default=None,
                    help="Last Excel row to process (inclusive, 1-based)")
    ap.add_argument("--out", default=None,
                    help="Output path (default: <input>.filled.xlsx)")
    ap.add_argument("--normalize", action="store_true",
                    help="Retry with normalized company names (drops Inc./LLC, punctuation)")
    ap.add_argument("--log-level", choices=["none", "warn", "all"], default="warn",
                    help="Console logging: none, warn (misses/pending), or all rows. Default: warn.")
    ap.add_argument("--reuse", action="store_true",
                    help="Reuse the same search page for all rows (no full reload). ~40% faster")
    args = ap.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        raise SystemExit(f"Input not found: {in_path}")

    # Load Excel
    df = pd.read_excel(
        in_path, sheet_name=args.sheet) if args.sheet else pd.read_excel(in_path)
    name_idx, lic_idx = get_col_indices(df, args.name_col, args.license_col)

    # Ensure the license column can hold text but skip slow conversions if already string
    if not ptypes.is_string_dtype(df.iloc[:, lic_idx]):
        df.iloc[:, lic_idx] = df.iloc[:, lic_idx].astype(  # type: ignore
            "string")  # type: ignore

    out_path = Path(args.out) if args.out else in_path.with_suffix(
        ".filled.xlsx")

    # Determine rows to process
    total = len(df)
    if args.start_row or args.end_row:
        # Excel row 2 -> index 0
        start_i = max((args.start_row or 2) - 2, 0)
        end_i = min(((args.end_row or (total + 1)) - 2), total - 1)
        rows_iter = range(start_i, end_i + 1)
    elif args.limit:
        rows_iter = range(min(args.limit, total))
    else:
        rows_iter = range(total)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=not args.headful, slow_mo=80 if args.headful else 0)
        context = browser.new_context(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"),
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()

        for i in tqdm(rows_iter, desc="Searching", disable=(args.log_level == "none")):
            # Read name
            try:
                # pyright: ignore[reportArgumentType]
                name = str(df.iat[i, name_idx]).strip()  # type: ignore
            except Exception:
                name = ""
            if not name or name.lower() in {"nan", "none"}:
                continue

            # Respect existing values unless overwrite
            current = str(df.iat[i, lic_idx]) if pd.notna(  # type: ignore
                df.iat[i, lic_idx]) else ""  # type: ignore
            if current and not args.overwrite:
                continue

            # Query
            result = "NA"
            try:
                result = fill_for_name(
                    page, name, delay_after=args.pause, try_normalized=args.normalize)
            except Exception as e:
                tqdm.write(f"  ! lookup failed for {name!r}: {e}")
                result = "NA"

            # Write: 'L.xxxxx' | 'PENDING' | 'NA'
            df.iat[i, lic_idx] = str(result) if pd.notna(  # type: ignore
                result) else "NA"  # type: ignore

            # Logging
            if args.log_level == "all":
                print(f'Row {i+2}: "{name}" -> {result}')
            elif args.log_level == "warn" and result in {"NA", "PENDING"}:
                print(f'Row {i+2}: "{name}" -> {result}')

            time.sleep(args.pause)

        browser.close()

    save_xlsx(df, out_path)


if __name__ == "__main__":
    main()
