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

APP_URL = "https://stockupdate-65qjxum6gq2gpjpr5exqfd.streamlit.app"


# ─────────────────────────────────────────────────────────────────────────────
# SIGNAL KLASSIFIKATION
# ─────────────────────────────────────────────────────────────────────────────

def classify_signal(stoch_rsi=None, stoch_fast=None, stoch_slow=None, cci=None, macd_turn=None) -> dict:
    """
    macd_turn: None (keine Aussage) | "up" (Histogramm dreht nach oben)
               | "down" (Histogramm dreht nach unten)
    Werte, die kein gültiges float sind (z.B. weil sie fehlen), müssen als
    None übergeben werden - nicht als 0.0! Ein 0.0-Fallback für fehlende
    Daten wird sonst fälschlich als "extrem" gewertet.
    """
    os_hits = ob_hits = 0
    if stoch_rsi  is not None:
        if stoch_rsi  < 0.15:  os_hits += 2
        elif stoch_rsi  > 0.85: ob_hits += 2
    if stoch_fast is not None:
        if stoch_fast < 20:    os_hits += 1
        elif stoch_fast > 80:  ob_hits += 1
    if stoch_slow is not None:
        if stoch_slow < 25:    os_hits += 1
        elif stoch_slow > 75:  ob_hits += 1
    if cci is not None:
        if cci < -100:  os_hits += 1
        elif cci > 100: ob_hits += 1
    if macd_turn == "up":     os_hits += 2   # MACD-Umkehr = eigentlicher Trigger der Strategie
    elif macd_turn == "down": ob_hits += 2

    is_extreme_os = os_hits >= 2 and os_hits > ob_hits
    is_extreme_ob = ob_hits >= 2 and ob_hits > os_hits

    if is_extreme_os and macd_turn == "up":
        return {"label":"KAUFSIGNAL", "emoji":"🟢","color":"#0d7a2e","bg":"#e8f9ed","short":"BUY"}
    elif is_extreme_ob and macd_turn == "down":
        return {"label":"VERKAUFSIGNAL","emoji":"🔴","color":"#8e1f14","bg":"#fdecea","short":"SELL"}
    elif is_extreme_os:
        return {"label":"OVERSOLD",   "emoji":"🟡","color":"#1a9e3f","bg":"#e8f9ed","short":"OS"}
    elif is_extreme_ob:
        return {"label":"OVERBOUGHT", "emoji":"🟠","color":"#c0392b","bg":"#fdecea","short":"OB"}
    else:
        return {"label":"NEUTRAL",    "emoji":"⚪","color":"#7f8c8d","bg":"#f4f4f4","short":"NT"}


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


# ─────────────────────────────────────────────────────────────────────────────
# SCANNER ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def get_analysis(ticker: str, retries: int = 2) -> dict | None:
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
            df['StochRSI'] = (df['RSI'] - df['RSI'].rolling(rsi_w).min()) / rsi_r

            slow_w = 200 if has_200 else 70
            hl_f   = (df['High'].rolling(70).max() - df['Low'].rolling(70).min()).replace(0, np.nan)
            df['Stoch_Fast'] = 100 * (df['Close'] - df['Low'].rolling(70).min()) / hl_f
            hl_s   = (df['High'].rolling(slow_w).max() - df['Low'].rolling(slow_w).min()).replace(0, np.nan)
            df['Stoch_Slow'] = 100 * (df['Close'] - df['Low'].rolling(slow_w).min()) / hl_s

            tp   = (df['High'] + df['Low'] + df['Close']) / 3
            mdev = tp.rolling(40).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
            df['CCI'] = (tp - tp.rolling(40).mean()) / (0.015 * mdev.replace(0, np.nan))

            df = compute_macd(df, fast=70 if has_70 else 12, slow=200 if has_200 else 26, signal=9)
            macd_turn = detect_macd_turn(df)

            def _s(v, d=3):
                try:
                    f = float(v); return round(f, d) if np.isfinite(f) else None
                except Exception: return None

            sv = _s(df['StochRSI'].iloc[-1])
            sf = _s(df['Stoch_Fast'].iloc[-1], 1)
            ss = _s(df['Stoch_Slow'].iloc[-1], 1)
            cv = _s(df['CCI'].iloc[-1], 1)

            # Score /4: die 3 Extremwert-Kriterien + MACD-Umkehr als eigentlicher Trigger
            score = 0
            if sv is not None and 0 < sv < 0.1:                          score += 1
            if sf is not None and ss is not None and sf < 10 and ss < 15: score += 1
            if cv is not None and cv > -100:                             score += 1
            if macd_turn == "up":                                        score += 1

            sig = classify_signal(sv, sf, ss, cv, macd_turn)

            inf = {}
            try: inf = stock.info or {}
            except Exception: pass
            cur   = get_currency(ticker)
            price = float(df['Close'].iloc[-1])

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

        score = 0
        if sr is not None and 0 < sr  < 0.2:  score += 1
        if sk is not None and sk  < 25:       score += 1
        if cci is not None and cci < -80:     score += 1
        if rsi_v is not None and rsi_v < 35:  score += 1

        sig   = classify_signal(sr, sk, sd, cci, macd_turn)
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

def send_mail_report(df_results, password, total_scanned=0, success_count=0, failed_count=0) -> str:
    try:
        sender, receiver = "daily@in8invest.com", "j.jendraszek@yahoo.de"
        signals = pd.DataFrame()
        if not df_results.empty and 'Score' in df_results.columns:
            signals = df_results[df_results['Score'] > 1].sort_values("Score", ascending=False)

        def _fmt(v, d=1):
            if v is None: return "N/A"
            try:
                fv = float(v)
                return f"{fv:.{d}f}" if np.isfinite(fv) else "N/A"
            except Exception:
                return "N/A"

        def _macd_text(v):
            if v == "up":   return "MACD ↑"
            if v == "down": return "MACD ↓"
            return "MACD –"

        def _card(r):
            sig  = classify_signal(r.get('StochRSI'), r.get('Stoch_Fast'), r.get('Stoch_Slow'),
                                    r.get('CCI'), r.get('MACD_Turn'))
            sc   = int(r.get('Score', 0))
            sc_c = {4:"#0d7a2e",3:"#1a9e3f",2:"#f39c12",1:"#7f8c8d"}.get(sc,"#999")
            url  = f"{APP_URL}/?ticker={r.get('Ticker','')}"
            detail = (f"StochRSI {_fmt(r.get('StochRSI'),3)} · Stoch F/S {_fmt(r.get('Stoch_Fast'))}/{_fmt(r.get('Stoch_Slow'))} · "
                      f"CCI {_fmt(r.get('CCI'))} · {_macd_text(r.get('MACD_Turn'))}")
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
            </div></a>"""

        buy_rows = signals[signals['Score'] == 4] if not signals.empty else signals
        watch_rows = signals[signals['Score'] < 4] if not signals.empty else signals

        buy_html   = "".join(_card(r) for _, r in buy_rows.iterrows()) if not buy_rows.empty else \
            "<div style='color:#94a3b8;font-size:13px;font-style:italic;padding:8px 4px'>Keine MACD-bestätigten Kaufsignale heute.</div>"
        watch_html = "".join(_card(r) for _, r in watch_rows.iterrows()) if not watch_rows.empty else \
            "<div style='color:#94a3b8;font-size:13px;font-style:italic;padding:8px 4px'>Keine weiteren Beobachtungskandidaten.</div>"

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
    <b style="color:#0f172a">{len(signals)} Signale</b> (davon <b style="color:#0d7a2e">{len(buy_rows)}</b> MACD-bestätigt)
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
  </div>

  <!-- LEGENDE, eingeklappt kompakt -->
  <div style="background:#fffbeb;border-left:3px solid #f59e0b;border-radius:0 8px 8px 0;
              padding:10px 12px;margin-bottom:14px;font-size:11px;color:#78350f;line-height:1.5">
    <b>Kriterien:</b> StochRSI(70)&lt;0.1 · Stoch Fast(70)&lt;10 &amp; Slow(200)&lt;15 · CCI(40)&gt;−100 · MACD(70,200,9)-Histogramm dreht.
    Score 4/4 = alle Kriterien inkl. MACD-Trigger erfüllt. Tippen öffnet die Detail-Analyse.
  </div>

  <!-- FOOTER -->
  <div style="text-align:center;color:#94a3b8;font-size:10px;padding:6px 0 16px">
    In8Invest Scanner · Automatisch generiert ·
    <a href="{APP_URL}" style="color:#3b82f6;text-decoration:none">App öffnen</a>
  </div>

</div></body></html>"""

        msg = MIMEMultipart()
        msg['Subject'] = f"📊 In8Invest | {len(buy_rows)} Kaufsignale, {len(signals)} Signale gesamt | {now}"
        msg['From']    = sender
        msg['To']      = receiver
        msg.attach(MIMEText(body, 'html'))

        with smtplib.SMTP_SSL("w01a1dc3.kasserver.com", 465) as s:
            s.login(sender, password)
            s.sendmail(sender, receiver, msg.as_string())
        return "✅ Mail erfolgreich versendet"
    except Exception as e:
        return f"❌ Fehler: {e}"
