# automation_script.py — Täglicher automatischer Scan für GitHub Actions

import os
import sys
import time
import logging
import pandas as pd
from database import get_all_tickers
from engine import get_analysis, send_mail_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def run_automation() -> None:
    email_pass = os.getenv("DAILY_EMAIL_PASS")
    if not email_pass:
        log.error("Secret 'DAILY_EMAIL_PASS' nicht gesetzt – Abbruch.")
        sys.exit(1)

    all_tickers   = get_all_tickers()
    total_scanned = len(all_tickers)
    results       = []
    failed        = []

    log.info(f"Starte Analyse von {total_scanned} Tickern …")

    for ticker in all_tickers:
        try:
            res = get_analysis(ticker)
            if res:
                results.append({k: v for k, v in res.items() if k != "df"})
            else:
                failed.append(ticker)
        except Exception as e:
            failed.append(ticker)
            log.warning(f"Fehler bei {ticker}: {e}")
        time.sleep(0.05)  # Rate-Limit-Schutz

    success_count = len(results)
    failed_count  = len(failed)
    log.info(f"Fertig — Erfolg: {success_count}, Fehler: {failed_count}")

    if failed:
        sample = ", ".join(failed[:20])
        log.info(f"Fehlgeschlagen: {sample}{'…' if len(failed) > 20 else ''}")

    df_results = pd.DataFrame(results) if results else pd.DataFrame()
    if not df_results.empty and "KGV" in df_results.columns:
        df_results["KGV"] = df_results["KGV"].astype(str)

    status = send_mail_report(
        df_results, email_pass,
        total_scanned=total_scanned,
        success_count=success_count,
        failed_count=failed_count,
    )
    log.info(status)


if __name__ == "__main__":
    run_automation()
