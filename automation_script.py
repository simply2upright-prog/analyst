# automation_script.py — Täglicher automatischer Scan für GitHub Actions

import os
import sys
import time
import logging
import numpy as np
import pandas as pd
from database import get_all_tickers, get_group_for_ticker
from engine import get_analysis, send_mail_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def _add_relative_strength(results: list[dict]) -> list[dict]:
    """
    Relative Stärke = eigene 20-Tage-Performance minus Durchschnitt der
    Peer-Gruppe (gleiche TICKER_LISTS-Gruppe) in diesem Scan-Lauf.
    Positiv = Ticker schlägt seine Vergleichsgruppe, negativ = schwächer
    als die Gruppe (z.B. bei einem Branchen-weiten Ausverkauf).
    """
    groups: dict[str, list[float]] = {}
    for r in results:
        grp = get_group_for_ticker(r["Ticker"])
        r["_group"] = grp
        if grp and r.get("Ret_20d") is not None:
            groups.setdefault(grp, []).append(r["Ret_20d"])

    group_avg = {g: round(float(np.mean(v)), 2) for g, v in groups.items() if v}

    for r in results:
        grp = r.pop("_group", None)
        avg = group_avg.get(grp)
        if avg is not None and r.get("Ret_20d") is not None:
            r["RelStrength"] = round(r["Ret_20d"] - avg, 2)
        else:
            r["RelStrength"] = None
    return results


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
            res = get_analysis(ticker, compute_history=True)
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

    results = _add_relative_strength(results)

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
