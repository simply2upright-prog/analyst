# engine.py — v4: Klickbare Email-Links, Signal-Klassifikation, Futures

import yfinance as yf
import pandas as pd
import numpy as np
import smtplib
import time
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from database import get_currency

APP_URL = "https://analyst-qvzhar3rttdg8rghfaxw63.streamlit.app/"


# ─────────────────────────────────────────────────────────────────────────────
# SIGNAL KLASSIFIKATION
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_criteria(stoch_rsi=None, stoch_fast=None, stoch_slow=None, cci=None, macd_turn=None) -> dict:
    """
    EINZIGE Stelle, an der die 4 Strategie-Kriterien ausgewertet werden.
    Sowohl der Score als auch das Signal-Label leiten sich aus genau
    denselben 4 Booleans ab - das verhindert die Klasse von Bugs, bei der
    ein Ticker als 'KAUFSIGNAL' markiert war, aber nur Score 3/4 hatte
    (weil Label und Score früher mit unterschiedlichen Schwellen gerechnet wurden).

    Kauf-Kriterien (aus der Original-Strategie):
      StochRSI(70) < 0.1
      Stoch Fast(70) < 10 UND Stoch Slow(7er-Glättung) < 15
      CCI(20) > -100          (Erholung aus dem überverkauften Bereich)
      MACD-Histogramm dreht nach oben (Trigger)
    Verkauf-Kriterien (symmetrisch gespiegelt):
      StochRSI(70) > 0.9
      Stoch Fast(70) > 90 UND Stoch Slow(7er-Glättung) > 85
      CCI(20) < 100            (Abkühlung aus dem überkauften Bereich)
      MACD-Histogramm dreht nach unten (Trigger)
    """
    buy = {
        "stochrsi": stoch_rsi  is not None and 0 < stoch_rsi < 0.1,
        "stoch":    stoch_fast is not None and stoch_slow is not None and stoch_fast < 10 and stoch_slow < 15,
        "cci":      cci is not None and cci > -100,
        "macd":     macd_turn == "up",
    }
    sell = {
        "stochrsi": stoch_rsi  is not None and stoch_rsi > 0.9,
        "stoch":    stoch_fast is not None and stoch_slow is not None and stoch_fast > 90 and stoch_slow > 85,
        "cci":      cci is not None and cci < 100,
        "macd":     macd_turn == "down",
    }
    buy_score  = sum(buy.values())
    sell_score = sum(sell.values())
    return {"buy": buy, "sell": sell, "buy_score": buy_score, "sell_score": sell_score}


def classify_signal(stoch_rsi=None, stoch_fast=None, stoch_slow=None, cci=None, macd_turn=None) -> dict:
    """
    Label + Score aus EINER gemeinsamen Kriterien-Auswertung (siehe evaluate_criteria).
    macd_turn: None | "up" | "down". Fehlende Werte müssen als None übergeben
    werden, nicht als 0.0 - sonst werden sie fälschlich als 'extrem' gewertet.
    """
    c = evaluate_criteria(stoch_rsi, stoch_fast, stoch_slow, cci, macd_turn)
    bs, ss = c["buy_score"], c["sell_score"]

    if bs == 4:
        r = {"label":"KAUFSIGNAL",  "emoji":"🟢","color":"#0d7a2e","bg":"#e8f9ed","short":"BUY"}
    elif ss == 4:
        r = {"label":"VERKAUFSIGNAL","emoji":"🔴","color":"#8e1f14","bg":"#fdecea","short":"SELL"}
    elif bs >= 2 and bs > ss:
        r = {"label":"OVERSOLD",   "emoji":"🟡","color":"#1a9e3f","bg":"#e8f9ed","short":"OS"}
    elif ss >= 2 and ss > bs:
        r = {"label":"OVERBOUGHT", "emoji":"🟠","color":"#c0392b","bg":"#fdecea","short":"OB"}
    else:
        r = {"label":"NEUTRAL",    "emoji":"⚪","color":"#7f8c8d","bg":"#f4f4f4","short":"NT"}
    r["buy_score"], r["sell_score"] = bs, ss
    r["score"] = bs if bs >= ss else -ss   # positiv=Kauf-Score, negativ=Verkauf-Score (für Sortierung)
    return r


# ─────────────────────────────────────────────────────────────────────────────
# GEMEINSAME HELPER
# ─────────────────────────────────────────────────────────────────────────────

def clean_price_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Entfernt Zeilen ohne gültigen Schlusskurs (z.B. der aktuelle Handelstag,
    wenn Yahoo Finance noch keine/unvollständige Daten geliefert hat - passiert
    v.a. am Wochenende oder direkt nach Handelsschluss). Ohne diesen Schritt
    landet z.T. 'nan' als aktueller Kurs im UI.
    """
    if df is None or df.empty:
        return df
    return df[df["Close"].notna()]


def compute_macd(df: pd.DataFrame, fast: int = 70, slow: int = 200, signal: int = 9) -> pd.DataFrame:
    """MACD mit EMA/EMA wie im Chart-Setup des Nutzers (Standard: 70/200/9)."""
    ema_fast = df["Close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["Close"].ewm(span=slow, adjust=False).mean()
    df["MACD"]   = ema_fast - ema_slow
    df["SIGNAL"] = df["MACD"].ewm(span=signal, adjust=False).mean()
    df["OSMA"]   = df["MACD"] - df["SIGNAL"]
    return df


def detect_macd_turn(df: pd.DataFrame, lookback: int = 3) -> str | None:
    """
    Erkennt eine Umkehr im MACD-Histogramm (OSMA) an den letzten `lookback` Balken:
    'up'   = Histogramm fiel und dreht jetzt nach oben (Kaufsignal-Trigger)
    'down' = Histogramm stieg und dreht jetzt nach unten (Verkaufssignal-Trigger)
    None   = keine klare Umkehr / zu wenig Daten
    """
    if "OSMA" not in df.columns or len(df) < lookback + 2:
        return None
    h = df["OSMA"].tail(lookback + 2).values
    if np.any(np.isnan(h)):
        return None
    # war fallend bis vorletztem Balken, letzter Balken höher als vorletzter
    was_falling = all(h[i] < h[i-1] for i in range(1, len(h)-1))
    turns_up    = h[-1] > h[-2]
    was_rising  = all(h[i] > h[i-1] for i in range(1, len(h)-1))
    turns_down  = h[-1] < h[-2]
    if was_falling and turns_up:
        return "up"
    if was_rising and turns_down:
        return "down"
    return None


def format_dividend_yield(info: dict, price: float) -> str:
    """
    yfinance liefert 'dividendYield' je nach Version mal als Bruchzahl (0.038)
    mal bereits als Prozentwert (3.8) - das führte zu Anzeigen wie '388%'.
    Robuster: wo möglich direkt aus dividendRate (Betrag je Aktie) / Kurs
    berechnen, das ist von der API-Version unabhängig.
    """
    rate = info.get("dividendRate")
    if isinstance(rate, (int, float)) and rate > 0 and isinstance(price, (int, float)) and price > 0:
        return f"{round(rate / price * 100, 2)}%"
    dy = info.get("dividendYield")
    if isinstance(dy, (int, float)) and dy > 0:
        pct = dy * 100 if dy < 1 else dy   # Heuristik für den Fraction/Percent-Mix
        return f"{round(pct, 2)}%"
    return "0.00%"


def macd_turn_at(df: pd.DataFrame, i: int, lookback: int = 3) -> str | None:
    """Wie detect_macd_turn(), aber für eine beliebige Position i im DataFrame (Backtest)."""
    if "OSMA" not in df.columns or i < lookback + 1:
        return None
    h = df["OSMA"].iloc[i - lookback - 1 : i + 1].values
    if len(h) < lookback + 2 or np.any(np.isnan(h)):
        return None
    was_falling = all(h[j] < h[j-1] for j in range(1, len(h)-1))
    turns_up    = h[-1] > h[-2]
    was_rising  = all(h[j] > h[j-1] for j in range(1, len(h)-1))
    turns_down  = h[-1] < h[-2]
    if was_falling and turns_up:   return "up"
    if was_rising and turns_down:  return "down"
    return None


def find_signal_history(df: pd.DataFrame, rsi_col="StochRSI_70", cci_col="CCI_20") -> list[dict]:
    """
    Findet alle historischen Momente, an denen die Kauf-Kriterien
    (StochRSI < 0.1, Stoch Fast < 10 & Slow < 15, CCI > -100, MACD-Umkehr)
    mit buy_score >= 2 erfüllt waren. Nutzt dieselbe evaluate_criteria()
    wie der Live-Scan - Historie und aktuelles Signal sind damit konsistent.
    """
    hits = []
    if len(df) < 20 or rsi_col not in df.columns or cci_col not in df.columns:
        return hits

    for i in range(len(df)):
        row = df.iloc[i]
        sr, sf, ss, cv = row.get(rsi_col), row.get('Stoch_Fast'), row.get('Stoch_Slow'), row.get(cci_col)
        if any(pd.isna(x) for x in [sr, sf, ss, cv]):
            continue
        macd_turn = macd_turn_at(df, i)
        c = evaluate_criteria(float(sr), float(sf), float(ss), float(cv), macd_turn)
        if c["buy_score"] >= 2:
            hits.append({
                "date": df.index[i], "price": round(float(row['Close']), 2),
                "StochRSI": round(float(sr), 3), "CCI": round(float(cv), 1),
                "MACD_Turn": macd_turn, "score": c["buy_score"],
            })
    return hits


def find_entry_signals(df: pd.DataFrame, rsi_col="StochRSI_70", cci_col="CCI_20") -> list[dict]:
    """
    Einstiegszeitpunkt-Logik: Kriterien erfüllt -> warte auf Bestätigung.
    Trigger (was zuerst eintritt): (a) MACD-Histogramm dreht nach oben
    (eigentlicher Trigger der Strategie), (b) ersatzweise Kurs > 2% über
    lokalem Tief. Mehrere Signale, die auf denselben Bestätigungstag laufen,
    werden zu einem Trade zusammengefasst (kein Doppelzählen in der Trefferquote).
    """
    entries = []
    signal_hits = find_signal_history(df, rsi_col, cci_col)

    for hit in signal_hits:
        try:
            hit_idx = df.index.get_loc(hit["date"])
            window  = df.iloc[hit_idx: min(hit_idx + 21, len(df))]
            if len(window) < 3:
                continue
            local_low = float(window['Low'].min())
            low_date  = window['Low'].idxmin()
            low_idx   = window.index.get_loc(low_date) if hasattr(window.index, 'get_loc') else 0
            confirm_window = window.iloc[low_idx:]

            macd_confirm_date = None
            for j in range(hit_idx, min(hit_idx + 21, len(df))):
                if macd_turn_at(df, j) == "up":
                    macd_confirm_date = df.index[j]
                    break

            price_confirm_rows = confirm_window[confirm_window['Close'] > local_low * 1.02]
            price_confirm_date = price_confirm_rows.index[0] if not price_confirm_rows.empty else None

            candidates = [(d, "MACD") for d in [macd_confirm_date] if d is not None] + \
                         [(d, "Preis") for d in [price_confirm_date] if d is not None]
            if not candidates:
                continue
            confirm_date, trigger = min(candidates, key=lambda t: t[0])
            confirm_price = round(float(df.loc[confirm_date, 'Close']), 2)

            entries.append({
                "signal_date":   hit["date"], "signal_price": hit["price"],
                "entry_date":    confirm_date, "entry_price":  confirm_price,
                "local_low":     round(local_low, 2),
                "days_to_entry": (confirm_date - hit["date"]).days,
                "upside_pct":    round((confirm_price - local_low) / local_low * 100, 1),
                "trigger":       trigger,
            })
        except Exception:
            continue

    entries.sort(key=lambda e: e["signal_date"])
    seen, deduped = set(), []
    for e in entries:
        if e["entry_date"] in seen: continue
        seen.add(e["entry_date"]); deduped.append(e)
    return deduped


def compute_hit_rate(entry_signals: list[dict], df: pd.DataFrame, forward_days: int = 40) -> dict:
    """
    Für jedes historische Einstiegssignal: fand danach eine echte Trendwende statt?
    (Kurs stieg innerhalb von `forward_days` Tagen um mind. 5% über den Einstiegspreis.)
    """
    if not entry_signals or df.empty:
        return {"total": 0, "hits": 0, "misses": 0, "rate": 0.0, "details": []}

    hits = misses = 0
    details = []
    cutoff = df.index[-forward_days] if len(df) > forward_days else df.index[0]

    for e in entry_signals:
        entry_date, entry_price = e["entry_date"], e["entry_price"]
        try:
            if entry_date > cutoff:
                details.append({"entry_date": entry_date, "entry_price": entry_price,
                                 "result": "⏳ Zu Neu", "result_code": "new", "max_gain_pct": None})
                continue
            fwd_data = df[df.index > entry_date].head(forward_days)
            if fwd_data.empty:
                continue
            max_close = float(fwd_data["Close"].max())
            max_gain  = round((max_close - entry_price) / entry_price * 100, 1) if entry_price else 0
            min_close = float(fwd_data["Close"].min())
            max_loss  = round((min_close - entry_price) / entry_price * 100, 1) if entry_price else 0

            if max_gain >= 10:
                result, result_code = "✅ Starke Wende", "strong"; hits += 1
            elif max_gain >= 5:
                result, result_code = "🟡 Schwache Wende", "weak"; hits += 1
            elif max_loss < -5 and max_gain < 3:
                result, result_code = "❌ Kein Boden", "fail"; misses += 1
            else:
                result, result_code = "⚠️ Seitwärts", "sideways"; misses += 1

            details.append({"entry_date": entry_date, "entry_price": entry_price, "result": result,
                             "result_code": result_code, "max_gain_pct": max_gain, "max_loss_pct": max_loss})
        except Exception:
            continue

    total = hits + misses
    rate  = round(hits / total, 2) if total > 0 else 0.0
    return {"total": total, "hits": hits, "misses": misses, "rate": rate, "details": details}


# ─────────────────────────────────────────────────────────────────────────────
# SCANNER ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def get_analysis(ticker: str, retries: int = 2, compute_history: bool = True) -> dict | None:
    """
    compute_history=True berechnet zusätzlich die historische Trefferquote
    (teurer, aber i.d.R. < 50ms zusätzlich pro Ticker - die Netzwerk-Zeit für
    yfinance dominiert die Laufzeit ohnehin, nicht diese Berechnung).
    """
    for attempt in range(retries + 1):
        try:
            stock = yf.Ticker(ticker)
            df    = stock.history(period="2y", auto_adjust=False)
            df    = clean_price_df(df)
            if df.empty or len(df) < 50:
                return None

            has_70  = len(df) >= 70
            has_200 = len(df) >= 200
            rsi_w   = 70 if has_70 else 14

            delta = df['Close'].diff()
            gain  = delta.where(delta > 0, 0.0).rolling(rsi_w).mean()
            loss  = (-delta.where(delta < 0, 0.0)).rolling(rsi_w).mean()
            df['RSI'] = 100 - (100 / (1 + gain / loss.replace(0, np.nan)))
            rsi_r     = (df['RSI'].rolling(rsi_w).max() - df['RSI'].rolling(rsi_w).min()).replace(0, np.nan)
            df['StochRSI_70'] = (df['RSI'] - df['RSI'].rolling(rsi_w).min()) / rsi_r

            slow_w = 200 if has_200 else 70
            hl_f   = (df['High'].rolling(70).max() - df['Low'].rolling(70).min()).replace(0, np.nan)
            df['Stoch_Fast'] = 100 * (df['Close'] - df['Low'].rolling(70).min()) / hl_f
            df['Stoch_Slow'] = df['Stoch_Fast'].rolling(7).mean()   # Stoch(70,7,1): Slow = 7er-Glättung von Fast

            tp   = (df['High'] + df['Low'] + df['Close']) / 3
            mdev = tp.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
            df['CCI_20'] = (tp - tp.rolling(20).mean()) / (0.015 * mdev.replace(0, np.nan))

            df = compute_macd(df, fast=70 if has_70 else 12, slow=200 if has_200 else 26, signal=9)
            macd_turn = detect_macd_turn(df)

            # Trendfilter: Kurs vs. SMA200 (vermeidet "überverkauft im freien Fall" als falsche Kaufchance)
            df['SMA200'] = df['Close'].rolling(min(200, len(df)-1)).mean()
            sma200 = df['SMA200'].iloc[-1]
            trend  = None
            if pd.notna(sma200):
                trend = "up" if df['Close'].iloc[-1] > sma200 else "down"

            def _s(v, d=3):
                try:
                    f = float(v); return round(f, d) if np.isfinite(f) else None
                except Exception: return None

            sv = _s(df['StochRSI_70'].iloc[-1])
            sf = _s(df['Stoch_Fast'].iloc[-1], 1)
            ss = _s(df['Stoch_Slow'].iloc[-1], 1)
            cv = _s(df['CCI_20'].iloc[-1], 1)

            sig   = classify_signal(sv, sf, ss, cv, macd_turn)
            score = sig["buy_score"] if sig["buy_score"] >= sig["sell_score"] else sig["sell_score"]

            # Historische Trefferquote (Formations-Check) - nur wenn genug Datenbasis vorhanden
            hit_rate_pct, hit_rate_n = None, 0
            if compute_history:
                try:
                    entries  = find_entry_signals(df)
                    hr       = compute_hit_rate(entries, df)
                    hit_rate_n = hr["total"]
                    if hit_rate_n >= 5:   # zu kleine Stichprobe ist statistisch nicht aussagekräftig
                        hit_rate_pct = round(hr["rate"] * 100, 0)
                except Exception:
                    pass

            inf = {}
            try: inf = stock.info or {}
            except Exception: pass
            cur   = get_currency(ticker)
            price = float(df['Close'].iloc[-1])
            price_20d_ago = float(df['Close'].iloc[-21]) if len(df) > 21 else None
            ret_20d = round((price - price_20d_ago) / price_20d_ago * 100, 2) if price_20d_ago else None

            return {
                "Ticker":     ticker,
                "Name":       inf.get('shortName', ticker)[:20],
                "Signal":     f"{sig['emoji']} {sig['label']}",
                "Preis":      f"{round(price,2)} {cur}",
                "Währung":    cur,
                "StochRSI":   sv,
                "CCI":        cv,
                "Stoch_Fast": sf,
                "Stoch_Slow": ss,
                "MACD_Turn":  macd_turn,
                "Score":      score,
                "Trend":      trend,               # "up" / "down" / None
                "HitRate":    hit_rate_pct,         # % oder None (zu wenig Historie)
                "HitRate_N":  hit_rate_n,
                "Ret_20d":    ret_20d,               # für relative Stärke (Gruppenvergleich in automation_script)
                "Div":        format_dividend_yield(inf, price),
                "KGV":        round(inf.get('trailingPE',0),1) if inf.get('trailingPE') else "N/A",
            }
        except Exception as e:
            if attempt < retries: time.sleep(1.0)
            else: print(f"[engine] {ticker}: {e}")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# FUTURES
# ─────────────────────────────────────────────────────────────────────────────

FUTURES_TICKERS = {
    "CL=F":  {"name":"Crude Oil (WTI)",     "group":"Energie",    "unit":"$/bbl"},
    "BZ=F":  {"name":"Brent Crude Oil",     "group":"Energie",    "unit":"$/bbl"},
    "NG=F":  {"name":"Natural Gas",         "group":"Energie",    "unit":"$/MMBtu"},
    "RB=F":  {"name":"RBOB Gasoline",       "group":"Energie",    "unit":"$/gal"},
    "HO=F":  {"name":"Heating Oil",         "group":"Energie",    "unit":"$/gal"},
    "GC=F":  {"name":"Gold",                "group":"Edelmetalle","unit":"$/oz"},
    "SI=F":  {"name":"Silber",              "group":"Edelmetalle","unit":"$/oz"},
    "PL=F":  {"name":"Platin",              "group":"Edelmetalle","unit":"$/oz"},
    "PA=F":  {"name":"Palladium",           "group":"Edelmetalle","unit":"$/oz"},
    "HG=F":  {"name":"Kupfer",              "group":"Edelmetalle","unit":"$/lb"},
    "ZC=F":  {"name":"Mais (Corn)",         "group":"Agrar",      "unit":"¢/bu"},
    "ZW=F":  {"name":"Weizen (Wheat)",      "group":"Agrar",      "unit":"¢/bu"},
    "ZS=F":  {"name":"Soja (Soybeans)",     "group":"Agrar",      "unit":"¢/bu"},
    "KC=F":  {"name":"Kaffee (Coffee)",     "group":"Agrar",      "unit":"¢/lb"},
    "CT=F":  {"name":"Baumwolle (Cotton)",  "group":"Agrar",      "unit":"¢/lb"},
    "SB=F":  {"name":"Zucker (Sugar)",      "group":"Agrar",      "unit":"¢/lb"},
    "CC=F":  {"name":"Kakao (Cocoa)",       "group":"Agrar",      "unit":"$/t"},
    "ES=F":  {"name":"S&P 500 Future",      "group":"Index",      "unit":"Pkt"},
    "NQ=F":  {"name":"NASDAQ 100 Future",   "group":"Index",      "unit":"Pkt"},
    "YM=F":  {"name":"Dow Jones Future",    "group":"Index",      "unit":"Pkt"},
    "RTY=F": {"name":"Russell 2000 Future", "group":"Index",      "unit":"Pkt"},
    "6E=F":  {"name":"EUR/USD Future",      "group":"FX",         "unit":""},
    "6J=F":  {"name":"JPY/USD Future",      "group":"FX",         "unit":""},
    "6B=F":  {"name":"GBP/USD Future",      "group":"FX",         "unit":""},
    "BTC=F": {"name":"Bitcoin Future",      "group":"Krypto",     "unit":"$"},
    "ETH=F": {"name":"Ethereum Future",     "group":"Krypto",     "unit":"$"},
}


def get_futures_analysis(ticker: str) -> dict | None:
    meta = FUTURES_TICKERS.get(ticker, {"name": ticker, "group": "Sonstige", "unit": ""})
    try:
        stock = yf.Ticker(ticker)
        df    = stock.history(period="1y", auto_adjust=False)
        df    = clean_price_df(df)
        if df.empty or len(df) < 30:
            return None

        rsi_w = 14
        delta = df['Close'].diff()
        gain  = delta.where(delta > 0, 0.0).rolling(rsi_w).mean()
        loss  = (-delta.where(delta < 0, 0.0)).rolling(rsi_w).mean()
        df['RSI'] = 100 - (100 / (1 + gain / loss.replace(0, np.nan)))
        rsi_r     = (df['RSI'].rolling(rsi_w).max() - df['RSI'].rolling(rsi_w).min()).replace(0, np.nan)
        df['StochRSI'] = (df['RSI'] - df['RSI'].rolling(rsi_w).min()) / rsi_r

        w14 = min(14, len(df)-1)
        hl  = (df['High'].rolling(w14).max() - df['Low'].rolling(w14).min()).replace(0, np.nan)
        df['Stoch_K'] = 100 * (df['Close'] - df['Low'].rolling(w14).min()) / hl
        df['Stoch_D'] = df['Stoch_K'].rolling(3).mean()

        tp   = (df['High'] + df['Low'] + df['Close']) / 3
        mdev = tp.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
        df['CCI'] = (tp - tp.rolling(20).mean()) / (0.015 * mdev.replace(0, np.nan))

        bb_w = min(50, len(df)-1)
        df['EMA50']    = df['Close'].ewm(span=bb_w, adjust=False).mean()
        std            = df['Close'].rolling(bb_w).std()
        df['BB_Upper'] = df['EMA50'] + 2 * std
        df['BB_Lower'] = df['EMA50'] - 2 * std

        w20 = min(20, len(df)-1)
        df['SMA20']   = df['Close'].rolling(w20).mean()
        df['Z_Score'] = (df['Close'] - df['SMA20']) / df['Close'].rolling(w20).std().replace(0, np.nan)
        df['RVOL']    = df['Volume'] / df['Volume'].rolling(w20).mean().replace(0, np.nan)

        df = compute_macd(df, fast=12, slow=26, signal=9)
        macd_turn = detect_macd_turn(df)

        def _s(v, d=2):
            try:
                f = float(v); return round(f, d) if np.isfinite(f) else None
            except Exception: return None

        price  = _s(df['Close'].iloc[-1])
        sr     = _s(df['StochRSI'].iloc[-1], 3)
        sk     = _s(df['Stoch_K'].iloc[-1], 1)
        sd     = _s(df['Stoch_D'].iloc[-1], 1)
        cci    = _s(df['CCI'].iloc[-1], 1)
        rsi_v  = _s(df['RSI'].iloc[-1], 1)
        zscore = _s(df['Z_Score'].iloc[-1], 2)
        rvol   = _s(df['RVOL'].iloc[-1], 2)

        # Score aus derselben Kriterien-Auswertung wie das Label (keine getrennten,
        # abweichenden Schwellen - siehe evaluate_criteria in engine.py).
        sig   = classify_signal(sr, sk, sd, cci, macd_turn)
        score = sig["buy_score"] if sig["buy_score"] >= sig["sell_score"] else sig["sell_score"]
        df_1y = df.tail(252)

        return {
            "Ticker":   ticker, "Name": meta["name"], "Gruppe": meta["group"],
            "Einheit":  meta["unit"], "Signal": f"{sig['emoji']} {sig['label']}",
            "Sig_Data": sig, "Preis": price,
            "52W_Hoch": _s(df_1y['High'].max()), "52W_Tief": _s(df_1y['Low'].min()),
            "Perf_1W":  _s(((df['Close'].iloc[-1]/df['Close'].iloc[-5])-1)*100 if len(df)>=5 else None, 2),
            "Perf_1M":  _s(((df['Close'].iloc[-1]/df['Close'].iloc[-22])-1)*100 if len(df)>=22 else None, 2),
            "RSI": rsi_v, "StochRSI": sr, "Stoch_K": sk, "Stoch_D": sd,
            "CCI": cci, "Z_Score": zscore, "RVOL": rvol, "MACD_Turn": macd_turn,
            "Score": score, "df": df,
        }
    except Exception as e:
        print(f"[futures] {ticker}: {e}")
        return None


def get_all_futures_groups() -> list:
    seen, r = set(), []
    for v in FUTURES_TICKERS.values():
        if v["group"] not in seen:
            seen.add(v["group"]); r.append(v["group"])
    return r


def get_futures_by_group(group: str) -> list:
    return [k for k, v in FUTURES_TICKERS.items() if v["group"] == group]


# ─────────────────────────────────────────────────────────────────────────────
# EMAIL — mit klickbaren Ticker-Links und App-Header-Link
# ─────────────────────────────────────────────────────────────────────────────

def send_mail_report(df_results, password, total_scanned=0, success_count=0, failed_count=0, max_cards=15) -> str:
    try:
        sender, receiver = "daily@in8invest.com", "j.jendraszek@yahoo.de"
        signals = pd.DataFrame()
        if not df_results.empty and 'Score' in df_results.columns:
            signals = df_results[df_results['Score'] > 1].copy()
            # Sortierung: Score zuerst, dann historische Trefferquote (unbekannt=ganz unten),
            # dann relative Stärke - das bringt die aussichtsreichsten Kandidaten nach oben,
            # nicht nur "irgendwas ist heute extrem".
            signals['_hr_sort']  = signals['HitRate'].apply(lambda v: v if pd.notna(v) else -1)
            signals['_rs_sort']  = signals['RelStrength'].apply(lambda v: v if pd.notna(v) else -999) if 'RelStrength' in signals.columns else 0
            signals = signals.sort_values(["Score","_hr_sort","_rs_sort"], ascending=False)

        def _fmt(v, d=1):
            if v is None or (isinstance(v,float) and not np.isfinite(v)): return "N/A"
            try:
                fv = float(v)
                return f"{fv:.{d}f}" if np.isfinite(fv) else "N/A"
            except Exception:
                return "N/A"

        def _macd_text(v):
            if v == "up":   return "MACD ↑"
            if v == "down": return "MACD ↓"
            return "MACD –"

        def _trend_badge(t):
            if t == "up":   return "<span style='color:#0d7a2e;font-weight:700'>📈 Aufwärtstrend</span>"
            if t == "down": return "<span style='color:#c0392b;font-weight:700'>📉 Abwärtstrend</span>"
            return "<span style='color:#94a3b8'>Trend n/a</span>"

        def _hitrate_text(r):
            hr, n = r.get('HitRate'), r.get('HitRate_N', 0)
            if hr is None or pd.isna(hr):
                return f"Trefferquote: zu wenig Historie ({int(n) if pd.notna(n) else 0})" if n else "Trefferquote: keine Historie"
            return f"Trefferquote {int(hr)}% ({int(n)} Signale)"

        def _relstrength_text(r):
            rs = r.get('RelStrength')
            if rs is None or pd.isna(rs): return None
            arrow = "↑" if rs >= 0 else "↓"
            return f"rel. Stärke {arrow} {rs:+.1f}% vs. Gruppe"

        def _card(r):
            sig  = classify_signal(r.get('StochRSI'), r.get('Stoch_Fast'), r.get('Stoch_Slow'),
                                    r.get('CCI'), r.get('MACD_Turn'))
            sc   = int(r.get('Score', 0))
            sc_c = {4:"#0d7a2e",3:"#1a9e3f",2:"#f39c12",1:"#7f8c8d"}.get(sc,"#999")
            url  = f"{APP_URL}/?ticker={r.get('Ticker','')}"
            detail = (f"StochRSI {_fmt(r.get('StochRSI'),3)} · Stoch F/S {_fmt(r.get('Stoch_Fast'))}/{_fmt(r.get('Stoch_Slow'))} · "
                      f"CCI {_fmt(r.get('CCI'))} · {_macd_text(r.get('MACD_Turn'))}")
            rs_text = _relstrength_text(r)
            extra_line = f"{_trend_badge(r.get('Trend'))} &nbsp;·&nbsp; {_hitrate_text(r)}" + (f" &nbsp;·&nbsp; {rs_text}" if rs_text else "")
            return f"""
            <a href="{url}" style="text-decoration:none;color:inherit">
            <div style="background:#fff;border-radius:12px;padding:14px 16px;margin-bottom:8px;
                        box-shadow:0 1px 4px rgba(0,0,0,.06);border-left:4px solid {sig['color']}">
              <table width="100%" cellpadding="0" cellspacing="0"><tr>
                <td>
                  <span style="font-weight:800;font-size:14px;color:#0f172a">{r.get('Ticker','')}</span>
                  <span style="color:#94a3b8;font-size:12px;margin-left:6px">{r.get('Name','')}</span><br>
                  <span style="background:{sig['color']};color:#fff;padding:2px 9px;border-radius:10px;
                               font-size:10px;font-weight:700;display:inline-block;margin-top:5px">{sig['emoji']} {sig['label']}</span>
                  <span style="background:{sc_c};color:#fff;padding:2px 8px;border-radius:10px;
                               font-size:10px;font-weight:700;margin-left:4px">{sc}/4</span>
                </td>
                <td style="text-align:right;vertical-align:top">
                  <span style="font-weight:800;font-size:15px;color:#0f172a">{r.get('Preis','')}</span><br>
                  <span style="color:#94a3b8;font-size:11px">Div {r.get('Div','')} · KGV {r.get('KGV','')}</span>
                </td>
              </tr></table>
              <div style="color:#64748b;font-size:11px;margin-top:8px;padding-top:8px;border-top:1px solid #f1f5f9">{detail}</div>
              <div style="color:#64748b;font-size:11px;margin-top:4px">{extra_line}</div>
            </div></a>"""

        buy_rows_all   = signals[signals['Score'] == 4] if not signals.empty else signals
        watch_rows_all = signals[signals['Score'] < 4]  if not signals.empty else signals

        # Top-N begrenzen, damit die Mail nicht wieder überladen wird - Rest ist über
        # die App einsehbar (dort sortiert nach denselben Kriterien filterbar).
        buy_rows   = buy_rows_all.head(max_cards)
        remaining_buy_slots = max(0, max_cards - len(buy_rows))
        watch_rows = watch_rows_all.head(remaining_buy_slots if len(buy_rows_all) >= max_cards else max_cards - len(buy_rows))

        buy_html   = "".join(_card(r) for _, r in buy_rows.iterrows()) if not buy_rows.empty else \
            "<div style='color:#94a3b8;font-size:13px;font-style:italic;padding:8px 4px'>Keine MACD-bestätigten Kaufsignale heute.</div>"
        watch_html = "".join(_card(r) for _, r in watch_rows.iterrows()) if not watch_rows.empty else \
            "<div style='color:#94a3b8;font-size:13px;font-style:italic;padding:8px 4px'>Keine weiteren Beobachtungskandidaten.</div>"

        n_hidden = len(signals) - len(buy_rows) - len(watch_rows)
        more_html = ""
        if n_hidden > 0:
            more_html = (f"<div style='text-align:center;padding:10px;color:#64748b;font-size:12px'>"
                         f"+ {n_hidden} weitere Signale in der App ansehen → "
                         f"<a href='{APP_URL}' style='color:#3b82f6;text-decoration:none;font-weight:700'>App öffnen</a></div>")

        now = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")

        body = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:'Segoe UI',Arial,sans-serif">
<div style="max-width:600px;margin:0 auto;padding:16px 12px">

  <!-- HEADER -->
  <div style="background:linear-gradient(135deg,#0f172a 0%,#1e293b 60%,#0f2744 100%);
              border-radius:16px;padding:20px 22px;margin-bottom:14px;
              border:1px solid #334155">
    <div style="font-size:20px;font-weight:900;color:#fff">📊 <span style="color:#38bdf8">In8</span>Invest</div>
    <div style="color:#94a3b8;font-size:12px;margin-top:4px">Daily Report · {now}</div>
    <a href="{APP_URL}" style="display:inline-block;margin-top:12px;background:#3b82f6;color:#fff;
       padding:8px 16px;border-radius:8px;text-decoration:none;font-weight:700;font-size:12px">App öffnen →</a>
  </div>

  <!-- KOMPAKTE STATISTIK -->
  <div style="color:#64748b;font-size:12px;margin-bottom:14px;text-align:center">
    {total_scanned} geprüft · {success_count} analysiert · {failed_count} Fehler ·
    <b style="color:#0f172a">{len(signals)} Signale</b> (davon <b style="color:#0d7a2e">{len(buy_rows_all)}</b> MACD-bestätigt) ·
    Top {len(buy_rows)+len(watch_rows)} angezeigt, sortiert nach Score + Trefferquote
  </div>

  <!-- KAUFSIGNALE (Score 4/4 = Extrem + MACD-Umkehr) -->
  <div style="margin-bottom:18px">
    <div style="font-size:14px;font-weight:800;color:#0f172a;margin-bottom:8px">
      🟢 Kaufsignale — Extrem + MACD-Bestätigung
    </div>
    {buy_html}
  </div>

  <!-- BEOBACHTUNGSLISTE (Score 2-3, wartet noch auf MACD) -->
  <div style="margin-bottom:14px">
    <div style="font-size:14px;font-weight:800;color:#0f172a;margin-bottom:8px">
      🟡 Beobachtungsliste — überverkauft, MACD noch ohne Umkehr
    </div>
    {watch_html}
    {more_html}
  </div>

  <!-- LEGENDE, eingeklappt kompakt -->
  <div style="background:#fffbeb;border-left:3px solid #f59e0b;border-radius:0 8px 8px 0;
              padding:10px 12px;margin-bottom:14px;font-size:11px;color:#78350f;line-height:1.5">
    <b>Kriterien:</b> StochRSI(70)&lt;0.1 · Stoch Fast(70)&lt;10 &amp; Slow(7er-Glättung)&lt;15 · CCI(20)&gt;−100 · MACD(70,200,9)-Histogramm dreht.
    Score 4/4 = alle Kriterien inkl. MACD-Trigger erfüllt. <b>Trend</b> = Kurs vs. SMA200 (Vorsicht bei Käufen im Abwärtstrend).
    <b>Trefferquote</b> = wie oft dieses Muster historisch (2 Jahre) zu einer echten Wende (+5%/40 Tage) führte, ab 5 Signalen aussagekräftig.
    <b>rel. Stärke</b> = 20-Tage-Performance vs. Durchschnitt der Vergleichsgruppe. Tippen öffnet die Detail-Analyse.
  </div>

  <!-- FOOTER -->
  <div style="text-align:center;color:#94a3b8;font-size:10px;padding:6px 0 16px">
    In8Invest Scanner · Automatisch generiert ·
    <a href="{APP_URL}" style="color:#3b82f6;text-decoration:none">App öffnen</a>
  </div>

</div></body></html>"""

        msg = MIMEMultipart()
        msg['Subject'] = f"📊 In8Invest | {len(buy_rows_all)} Kaufsignale, {len(signals)} Signale gesamt | {now}"
        msg['From']    = sender
        msg['To']      = receiver
        msg.attach(MIMEText(body, 'html'))

        with smtplib.SMTP_SSL("w01a1dc3.kasserver.com", 465) as s:
            s.login(sender, password)
            s.sendmail(sender, receiver, msg.as_string())
        return "✅ Mail erfolgreich versendet"
    except Exception as e:
        return f"❌ Fehler: {e}"
