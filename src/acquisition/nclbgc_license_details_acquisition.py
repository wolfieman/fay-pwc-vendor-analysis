"""
nclbgc_license_details_acquisition.py — Scrape contractor license details from the
NC Licensing Board for General Contractors (NCLBGC) portal for a list of license
numbers (Selenium + webdriver-manager). AJAX-safe; splits multiple qualifiers into
separate columns. Outputs an Excel file.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import argparse
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Dict, Tuple

import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from vendorscope.columns import autodetect_license_column
from vendorscope.text import normalize_license


# --------------------------- configuration & CLI ------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="NCLBGC license details scraper")
    p.add_argument("--input", required=True, help="Input Excel file")
    p.add_argument("--sheet", default=None, help="Sheet name (optional)")
    p.add_argument(
        "--license-col",
        default=None,
        help="Column name with license numbers (auto-detects if omitted)",
    )
    p.add_argument(
        "--out",
        default="data/raw/nclbgc-license-details.xlsx",
        help="Output Excel file",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of licenses to process (for quick tests)",
    )
    p.add_argument("--headless", action="store_true", help="Run Chrome headless")
    p.add_argument(
        "--pause", type=float, default=0.25, help="Short sleep between actions (sec)"
    )
    return p.parse_args()


# ------------------------------- utilities -----------------------------------
def ts_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


# ------------------------------ scraper core ---------------------------------
@dataclass
class ScraperConfig:
    base_url: str = "https://portal.nclbgc.org/Public/Search"
    headless: bool = False
    small_pause: float = 0.25
    wait_seconds: int = 25


class NCLBGCDetailsScraper:
    def __init__(self, cfg: ScraperConfig):
        self.cfg = cfg
        self.driver: Chrome = self._init_driver()
        self.wait = WebDriverWait(self.driver, self.cfg.wait_seconds)
        self._detail_context = None  # dialog-form element

    def _init_driver(self) -> Chrome:
        opts = Options()
        if self.cfg.headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
        opts.add_argument("--window-size=1400,1000")
        service = Service(ChromeDriverManager().install())
        drv = webdriver.Chrome(service=service, options=opts)
        drv.set_page_load_timeout(45)
        return drv

    # ------------------------ debug helpers -------------------------
    def _dump_debug(self, tag: str) -> None:
        try:
            name = (
                f"debug_detail_missing_{ts_utc()}"
                if tag == "detail_missing"
                else f"debug_{tag}_{ts_utc()}"
            )
            with open(f"{name}.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            try:
                self.driver.save_screenshot(f"{name}.png")
            except Exception:
                pass
            print(f"Wrote debug snapshot {name}.html")
        except Exception:
            pass

    # ------------------------- navigation ---------------------------
    def open_search(self) -> None:
        self.driver.get(self.cfg.base_url)
        time.sleep(self.cfg.small_pause)
        # handle iframe if present
        try:
            self.driver.switch_to.default_content()
            for fr in self.driver.find_elements(By.TAG_NAME, "iframe"):
                self.driver.switch_to.frame(fr)
                if self.driver.find_elements(By.ID, "AccountNumber"):
                    return
                self.driver.switch_to.default_content()
        except Exception:
            pass

    def _find_search_input(self):
        selectors = [
            (By.ID, "AccountNumber"),
            (By.ID, "LicenseNumber"),
            (By.XPATH, "//input[@name='AccountNumber']"),
            (
                By.XPATH,
                "//input[contains(@placeholder,'License') or contains(@aria-label,'License')]",
            ),
            (By.XPATH, "//label[contains(.,'License Number')]/following::input[1]"),
        ]
        for by, sel in selectors:
            try:
                return self.driver.find_element(by, sel)
            except Exception:
                continue
        return None

    def search_license(self, lic: str) -> bool:
        self.open_search()
        inp = self._find_search_input()
        if not inp:
            print("⚠️  Could not find search input.")
            self._dump_debug("input_missing")
            return False

        try:
            inp.clear()
        except Exception:
            pass
        inp.send_keys(lic)
        time.sleep(self.cfg.small_pause)
        # press Enter or click Search
        try:
            inp.send_keys(Keys.ENTER)
        except Exception:
            try:
                self.driver.find_element(By.ID, "subBtn").click()
            except Exception:
                pass

        # Wait for results table containing an anchor with ShowAccountDetails
        try:
            self.wait.until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//table[@id='AccountSearchTable']//a[contains(@onclick,'ShowAccountDetails')]",
                    )
                )
            )
        except TimeoutException:
            print("⚠️  Search results did not load.")
            self._dump_debug("search_timeout")
            return False

        # Click the result anchor matching the license (prefer exact "L.<lic>")
        clicked = False
        xpaths = [
            f"//table[@id='AccountSearchTable']//a[normalize-space()=concat('L.','{lic}')]",
            f"//table[@id='AccountSearchTable']//a[contains(normalize-space(),'{lic}')]",
            "//table[@id='AccountSearchTable']//a[contains(@onclick,'ShowAccountDetails')]",
        ]
        for xp in xpaths:
            try:
                link = self.wait.until(EC.element_to_be_clickable((By.XPATH, xp)))
                link.click()
                clicked = True
                break
            except Exception:
                continue

        if not clicked:
            print("⚠️  Could not click into detail view.")
            self._dump_debug("click_detail_failed")
            return False

        # Wait for the inline dialog to be visible and populated via AJAX
        try:
            self.wait.until(EC.visibility_of_element_located((By.ID, "dialog-form")))
            self.wait.until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//*[@id='dialog-details']//*[contains(@class,'display-label')]",
                    )
                )
            )
            self._detail_context = self.driver.find_element(By.ID, "dialog-form")
            return True
        except TimeoutException:
            print("Detail view did not show expected elements")
            self._dump_debug("detail_missing")
            return False

    # ---------------------- extraction helpers ----------------------
    def _get_field_by_label(self, label_text: str) -> str:
        root = self._detail_context if self._detail_context is not None else self.driver
        xpath_exact = (
            ".//*[@id='dialog-details']//*[contains(@class,'display-label')][normalize-space()=$LX]/"
            "following-sibling::*[contains(@class,'display-field')][1]"
        ).replace("$LX", f"'{label_text}'")
        xpath_relaxed = (
            ".//*[@id='dialog-details']//*[contains(@class,'display-label')]"
            "[translate(normalize-space(),'#.:','')=translate($LX,'#.:','')]/"
            "following-sibling::*[contains(@class,'display-field')][1]"
        ).replace("$LX", f"'{label_text}'")
        for xp in (xpath_exact, xpath_relaxed):
            try:
                el = root.find_element(By.XPATH, xp)
                return el.text.strip()
            except Exception:
                continue
        return ""

    def _extract_qualifiers(self) -> Tuple[str, str, str]:
        """
        Returns (Qualifier_Number, Qualifier_Name, Qualifier_Status).
        If multiple rows exist, each field returns '; ' separated values aligned by row.
        Robust even if _detail_context is None.
        """
        q_nums: List[str] = []
        q_names: List[str] = []
        q_statuses: List[str] = []

        root = self._detail_context if self._detail_context is not None else self.driver
        try:
            # If we're on the page root, narrow to the dialog panel when present
            try:
                root = root.find_element(By.ID, "dialog-form")
            except Exception:
                pass

            # Hint that qualifiers section/table exists (don't fail if timeout)
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located(
                        (
                            By.XPATH,
                            "//*[@id='dialog-form']//legend[normalize-space()='Qualifiers'] | "
                            "//*[@id='dialog-form']//th[contains(normalize-space(),'Qualifier')]",
                        )
                    )
                )
            except TimeoutException:
                pass

            # Find qualifiers table using multiple fallbacks
            tables = root.find_elements(
                By.XPATH,
                ".//fieldset[.//legend[normalize-space()='Qualifiers']]//table | "
                ".//table[.//th[contains(normalize-space(),'Qualifier')]]",
            )
            if not tables:
                return "", "", ""

            table = tables[0]
            rows = table.find_elements(By.XPATH, ".//tr[td]")
            for r in rows:
                tds = r.find_elements(By.XPATH, ".//td")
                # Expected order: Name | Qualifier # | Status (defensive indexing)
                name = (tds[0].text if len(tds) > 0 else "").strip().replace("\n", " ")
                qnum = (tds[1].text if len(tds) > 1 else "").strip().replace("\n", " ")
                stat = (tds[2].text if len(tds) > 2 else "").strip().replace("\n", " ")
                if name or qnum or stat:
                    q_names.append(name)
                    q_nums.append(qnum)
                    q_statuses.append(stat)

        except Exception:
            return "", "", ""

        return "; ".join(q_nums), "; ".join(q_names), "; ".join(q_statuses)

    def extract_license_details(self) -> Dict[str, str]:
        if self._detail_context is None:
            print("Detail view not ready")
            self._dump_debug("detail_missing")
            return {"Error": "Detail context not found"}

        details: Dict[str, str] = {}
        try:
            # Contact
            details["Company_Name"] = self._get_field_by_label("Name")
            details["Full_Address"] = self._get_field_by_label("Address")
            details["Phone"] = self._get_field_by_label("Phone")

            # License
            details["License_Display"] = self._get_field_by_label(
                "License #"
            ) or self._get_field_by_label("License Number")
            details["Account_Type"] = self._get_field_by_label("Account Type")
            details["Issue_Date"] = self._get_field_by_label(
                "First Issued Date"
            ) or self._get_field_by_label("Issued Date")
            details["Expiration_Date"] = self._get_field_by_label("Expiration Date")
            details["Status"] = self._get_field_by_label("Status")
            details["License_Limitation"] = self._get_field_by_label(
                "License Limitation"
            )

            # Active Classifications
            classes_text = ""
            try:
                node = self._detail_context.find_element(
                    By.XPATH,
                    ".//fieldset[.//legend[normalize-space()='Active Classifications']]"
                    "//*[contains(@class,'display-field')][1]",
                )
                classes_text = node.text.strip().replace("\n", "; ")
            except Exception:
                try:
                    node = self._detail_context.find_element(
                        By.XPATH,
                        ".//*[contains(normalize-space(),'Classifications')]/following::*"
                        "[contains(@class,'display-field')][1]",
                    )
                    classes_text = node.text.strip().replace("\n", "; ")
                except Exception:
                    classes_text = ""
            details["Classifications"] = classes_text

            # Qualifiers → split into 3 dedicated columns
            qnum, qname, qstat = self._extract_qualifiers()
            details["Qualifier_Number"] = qnum
            details["Qualifier_Name"] = qname
            details["Qualifier_Status"] = qstat

        except Exception as e:
            print("Extraction error type " + e.__class__.__name__)
            try:
                print("Extraction error repr " + repr(e))
            except Exception:
                pass
            self._dump_debug("extract_exception")

        return details

    def close(self) -> None:
        try:
            self.driver.quit()
        except Exception:
            pass


# ------------------------------ main flow ------------------------------------
def run_scrape(
    input_file: str,
    sheet: Optional[str],
    license_col: Optional[str],
    out_file: str,
    limit: Optional[int],
    headless: bool,
    pause: float,
) -> None:
    print(f"Loading {input_file}")
    df = (
        pd.read_excel(input_file, sheet_name=sheet)
        if sheet
        else pd.read_excel(input_file)
    )
    col = license_col or autodetect_license_column(df)
    if not col:
        raise RuntimeError(
            "Could not find a license number column. Use --license-col to specify it."
        )

    lic_list: List[str] = []
    for v in df[col].tolist():
        n = normalize_license(v)
        if n:
            lic_list.append(n)
    if limit:
        lic_list = lic_list[:limit]
    print(f"Processing {len(lic_list)} licenses")

    cfg = ScraperConfig(headless=headless, small_pause=pause)
    scraper = NCLBGCDetailsScraper(cfg)

    results: List[Dict[str, str]] = []
    try:
        for idx, lic in enumerate(lic_list, 1):
            print(f"[{idx}/{len(lic_list)}] License {lic}")
            print(f"Searching for license {lic}")
            if not scraper.search_license(lic):
                results.append(
                    {"License_Number": lic, "Error": "Search or click failed"}
                )
                continue

            details = scraper.extract_license_details()
            row = {"License_Number": lic}
            row.update(details if details else {"Error": "Not found"})
            results.append(row)
            time.sleep(pause)
    finally:
        scraper.close()

    out = pd.DataFrame(results)

    # Desired column order (L: Qualifier_Number, M: Qualifier_Name, N: Qualifier_Status)
    ordered = [
        "License_Number",
        "Company_Name",
        "Full_Address",
        "Phone",
        "License_Display",
        "Account_Type",
        "Issue_Date",
        "Expiration_Date",
        "Status",
        "License_Limitation",
        "Classifications",
        "Qualifier_Number",
        "Qualifier_Name",
        "Qualifier_Status",
    ]
    cols = [c for c in ordered if c in out.columns] + [
        c for c in out.columns if c not in ordered
    ]
    out = out[cols]

    out.to_excel(out_file, index=False)
    print(f"Saved: {out_file}")
    print(f"Records: {len(out)}")


def main():
    args = parse_args()
    run_scrape(
        args.input,
        args.sheet,
        args.license_col,
        args.out,
        args.limit,
        args.headless,
        args.pause,
    )


if __name__ == "__main__":
    main()
