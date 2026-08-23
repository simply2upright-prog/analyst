# detail_engine.py — v4: Einstiegszeitpunkte, Marker-Historie, Boden/Top-Ziele

import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
from database import get_currency
from engine import classify_signal, clean_price_df, compute_macd, detect_macd_turn, format_dividend_yield


def _fetch_history(ticker: str):
    stock = yf.Ticker(ticker)
    df    = clean_price_df(stock.history(period="2y", auto_adjust=False))
    if df.empty or len(df) < 50:
        df = clean_price_df(stock.history(period="1y", auto_adjust=False))
    return df, stock


def get_detail_analysis(ticker: str) -> dict | None:
    try:
        df, stock = _fetch_history(ticker)
        if df.empty or len(df) < 50:
            return None

        has_200 = len(df) >= 200
        has_70  = len(df) >= 70
        rsi_w   = 70 if has_70 else 14

        # ── Indikatoren ────────────────────────────────────────────
        delta = df['Close'].diff()
        gain  = delta.where(delta > 0, 0.0).rolling(rsi_w).mean()
        loss  = (-delta.where(delta < 0, 0.0)).rolling(rsi_w).mean()
        df['RSI_70'] = 100 - (100 / (1 + gain / loss.replace(0, np.nan)))

        rsi_r = (df['RSI_70'].rolling(rsi_w).max() - df['RSI_70'].rolling(rsi_w).min()).replace(0, np.nan)
        df['StochRSI_70'] = (df['RSI_70'] - df['RSI_70'].rolling(rsi_w).min()) / rsi_r

        w14 = min(14, len(df)-1)
        hl  = (df['High'].rolling(w14).max() - df['Low'].rolling(w14).min()).replace(0, np.nan)
        df['Stoch_Fast'] = 100 * (df['Close'] - df['Low'].rolling(w14).min()) / hl
        df['Stoch_Slow'] = df['Stoch_Fast'].rolling(7).mean()

        tp   = (df['High'] + df['Low'] + df['Close']) / 3
        mdev = tp.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
        df['CCI_20'] = (tp - tp.rolling(20).mean()) / (0.015 * mdev.replace(0, np.nan))

        bb_w = 200 if has_200 else 50
        df['SMA200']   = df['Close'].ewm(span=bb_w, adjust=False).mean()
        std_bb         = df['Close'].rolling(bb_w).std()
        df['BB_Upper'] = df['SMA200'] + 2 * std_bb
        df['BB_Lower'] = df['SMA200'] - 2 * std_bb

        w20 = min(20, len(df)-1)
        df['SMA20']   = df['Close'].rolling(w20).mean()
        df['Z_Score'] = (df['Close'] - df['SMA20']) / df['Close'].rolling(w20).std().replace(0, np.nan)
        df['RVOL']    = df['Volume'] / df['Volume'].rolling(w20).mean().replace(0, np.nan)

        df = compute_macd(df, fast=70 if has_70 else 12, slow=200 if has_200 else 26, signal=9)
        macd_turn = detect_macd_turn(df)

        # ── Muster, Ziele, historische Marker ─────────────────────
        patterns, targets = _detect_patterns_and_targets(df)
        signal_history    = _find_signal_history(df)
        entry_signals     = _find_entry_signals(df)

        def _s(v, d=3):
            try:
                f = float(v); return round(f, d) if np.isfinite(f) else None
            except Exception: return None

        price         = float(df['Close'].iloc[-1])
        prev          = float(df['Close'].iloc[-2]) if len(df) >= 2 else price
        stoch_rsi_val = _s(df['StochRSI_70'].iloc[-1])
        s_fast        = _s(df['Stoch_Fast'].iloc[-1], 1)
        s_slow        = _s(df['Stoch_Slow'].iloc[-1], 1)
        cci_val       = _s(df['CCI_20'].iloc[-1], 1)

        # Score /4: die 3 Extremwert-Kriterien + MACD-Umkehr als eigentlicher Trigger
        score = 0
        if stoch_rsi_val is not None and 0 < stoch_rsi_val < 0.1:                         score += 1
        if s_fast is not None and s_slow is not None and s_fast < 20 and s_slow < 25:     score += 1
        if cci_val is not None and cci_val > -100:                                        score += 1
        if macd_turn == "up":                                                             score += 1

        sig = classify_signal(stoch_rsi_val, s_fast, s_slow, cci_val, macd_turn)

        inf = {}
        try: inf = stock.info or {}
        except Exception: pass

        currency = get_currency(ticker)
        div_str  = format_dividend_yield(inf, price)
        df_1y    = df.tail(252)

        return {
            "Ticker":         ticker,
            "Name":           inf.get('shortName', ticker)[:25],
            "Währung":        currency,
            "Signal":         f"{sig['emoji']} {sig['label']}",
            "Sig_Data":       sig,
            "Preis":          round(price, 2),
            "Perf_Abs":       round(price - prev, 2),
            "Perf_Pct":       round((price-prev)/prev*100 if prev else 0, 2),
            "Hoch_365":       round(float(df_1y['High'].max()), 2),
            "Tief_365":       round(float(df_1y['Low'].min()), 2),
            "Score":          score,
            "StochRSI":       stoch_rsi_val,
            "Stoch_Fast":     s_fast,
            "Stoch_Slow":     s_slow,
            "CCI":            cci_val,
            "Z_Score":        _s(df['Z_Score'].iloc[-1], 2),
            "RVOL":           _s(df['RVOL'].iloc[-1], 2),
            "MACD_Turn":      macd_turn,
            "MACD":           _s(df['MACD'].iloc[-1], 3),
            "MACD_Signal":    _s(df['SIGNAL'].iloc[-1], 3),
            "MACD_Hist":      _s(df['OSMA'].iloc[-1], 3),
            "Div":            div_str,
            "KGV":            round(inf.get('trailingPE',0),1) if inf.get('trailingPE') else "N/A",
            "Patterns":       patterns,
            "Targets":        targets,
            "Signal_History": signal_history,  # historische Indikator-Treffer
            "Entry_Signals":  entry_signals,   # Einstiegszeitpunkte
            "df":             df,
        }
    except Exception as e:
        print(f"[detail_engine] {ticker}: {e}")
        return None


def _macd_turn_at(df: pd.DataFrame, i: int, lookback: int = 3) -> str | None:
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


def _find_signal_history(df: pd.DataFrame) -> list[dict]:
    """
    Findet alle historischen Momente, an denen die Scanner-Kriterien
    (StochRSI < 0.1, Stoch Fast < 20, CCI > -100, MACD-Umkehr) erfüllt waren.
    Gibt Liste von {date, price, stochrsi, cci, macd_turn, score} zurück.
    """
    hits = []
    if len(df) < 20:
        return hits

    for i in range(len(df)):
        row = df.iloc[i]
        sr  = row.get('StochRSI_70', np.nan)
        sf  = row.get('Stoch_Fast',  np.nan)
        ss  = row.get('Stoch_Slow',  np.nan)
        cv  = row.get('CCI_20',      np.nan)

        if any(pd.isna(x) for x in [sr, sf, ss, cv]):
            continue

        macd_turn = _macd_turn_at(df, i)

        sc = 0
        if 0 < float(sr) < 0.1:                         sc += 1
        if float(sf) < 20 and float(ss) < 25:            sc += 1
        if float(cv) > -100:                             sc += 1
        if macd_turn == "up":                            sc += 1

        if sc >= 2:
            hits.append({
                "date":      df.index[i],
                "price":     round(float(row['Close']), 2),
                "StochRSI":  round(float(sr), 3),
                "CCI":       round(float(cv), 1),
                "MACD_Turn": macd_turn,
                "score":     sc,
            })

    # Cluster zusammenfassen: nur erste Treffer pro Cluster (min 10 Tage Abstand)
    clustered = []
    last_date = None
    for h in hits:
        if last_date is None or (h["date"] - last_date).days >= 10:
            clustered.append(h)
            last_date = h["date"]

    return clustered


def _find_entry_signals(df: pd.DataFrame) -> list[dict]:
    """
    Einstiegszeitpunkt-Logik:
    Kriterien waren erfüllt → warte auf Bestätigung. Zwei mögliche Trigger,
    es zählt was zuerst eintritt:
      (a) MACD-Histogramm dreht nach oben (der eigentliche Trigger der Strategie)
      (b) Ersatzweise: Kurs steigt > 2% über lokales Tief (falls MACD im Fenster nicht dreht)
    Gibt konkrete Einstiegssignale mit Datum, Preis, Trigger-Art und Vorlauf zurück.
    Mehrere Signal-Daten, die auf denselben Bestätigungstag laufen, werden zu
    EINEM Trade zusammengefasst (sonst wird derselbe Trade in der Trefferquote
    mehrfach gezählt und die Quote künstlich aufgebläht).
    """
    entries = []
    signal_hits = _find_signal_history(df)

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

            # (a) MACD-Umkehr im Fenster suchen
            macd_confirm_date = None
            for j in range(hit_idx, min(hit_idx + 21, len(df))):
                if _macd_turn_at(df, j) == "up":
                    macd_confirm_date = df.index[j]
                    break

            # (b) Preis-Bestätigung als Ersatz
            price_confirm_rows = confirm_window[confirm_window['Close'] > local_low * 1.02]
            price_confirm_date = price_confirm_rows.index[0] if not price_confirm_rows.empty else None

            candidates = [(d, "MACD") for d in [macd_confirm_date] if d is not None] + \
                         [(d, "Preis") for d in [price_confirm_date] if d is not None]
            if not candidates:
                continue
            confirm_date, trigger = min(candidates, key=lambda t: t[0])
            confirm_price = round(float(df.loc[confirm_date, 'Close']), 2)
            days_to_entry = (confirm_date - hit["date"]).days

            entries.append({
                "signal_date":    hit["date"],
                "signal_price":   hit["price"],
                "entry_date":     confirm_date,
                "entry_price":    confirm_price,
                "local_low":      round(local_low, 2),
                "days_to_entry":  days_to_entry,
                "upside_pct":     round((confirm_price - local_low) / local_low * 100, 1),
                "trigger":        trigger,
            })
        except Exception:
            continue

    # Dedupe: mehrere Signale, die zum selben Einstiegstag führen, zählen nur einmal
    # (sonst wird derselbe Trade in der Trefferquote doppelt gewertet)
    entries.sort(key=lambda e: e["signal_date"])
    seen_entry_dates = set()
    deduped = []
    for e in entries:
        if e["entry_date"] in seen_entry_dates:
            continue
        seen_entry_dates.add(e["entry_date"])
        deduped.append(e)

    return deduped


def compute_hit_rate(entry_signals: list[dict], df: pd.DataFrame, forward_days: int = 40) -> dict:
    """
    Berechnet für jedes historische Einstiegssignal, ob danach eine
    echte Trendwende stattgefunden hat.
    
    Kriterium Trendwende: Kurs stieg innerhalb von `forward_days` Tagen
    um mind. 5% über den Einstiegspreis.
    
    Gibt zurück:
    {
      "total": int,
      "hits": int,           # echte Bodenbildung bestätigt
      "misses": int,         # kein Anstieg >5%
      "rate": float,         # 0.0–1.0
      "details": list[dict]  # pro Signal: date, entry_price, result, max_gain_pct
    }
    """
    if not entry_signals or df.empty:
        return {"total": 0, "hits": 0, "misses": 0, "rate": 0.0, "details": []}

    hits   = 0
    misses = 0
    details = []
    # Wir brauchen mind. forward_days Zukunftsdaten → letzte Signale ausschließen
    cutoff = df.index[-forward_days] if len(df) > forward_days else df.index[0]

    for e in entry_signals:
        entry_date  = e["entry_date"]
        entry_price = e["entry_price"]

        # Signal zu nah am Ende → kein Forward-Window
        try:
            if entry_date > cutoff:
                details.append({
                    "entry_date":  entry_date,
                    "entry_price": entry_price,
                    "result":      "⏳ Zu Neu",
                    "result_code": "new",
                    "max_gain_pct": None,
                })
                continue

            fwd_data = df[df.index > entry_date].head(forward_days)
            if fwd_data.empty:
                continue

            max_close   = float(fwd_data["Close"].max())
            max_gain    = round((max_close - entry_price) / entry_price * 100, 1) if entry_price else 0
            min_close   = float(fwd_data["Close"].min())
            max_loss    = round((min_close - entry_price) / entry_price * 100, 1) if entry_price else 0

            # Bewertung
            if max_gain >= 10:
                result = "✅ Starke Wende"
                result_code = "strong"
                hits += 1
            elif max_gain >= 5:
                result = "🟡 Schwache Wende"
                result_code = "weak"
                hits += 1
            elif max_loss < -5 and max_gain < 3:
                result = "❌ Kein Boden"
                result_code = "fail"
                misses += 1
            else:
                result = "⚠️ Seitwärts"
                result_code = "sideways"
                misses += 1

            details.append({
                "entry_date":   entry_date,
                "entry_price":  entry_price,
                "result":       result,
                "result_code":  result_code,
                "max_gain_pct": max_gain,
                "max_loss_pct": max_loss,
            })
        except Exception:
            continue

    total = hits + misses
    rate  = round(hits / total, 2) if total > 0 else 0.0

    return {
        "total":   total,
        "hits":    hits,
        "misses":  misses,
        "rate":    rate,
        "details": details,
    }


def _detect_patterns_and_targets(df: pd.DataFrame) -> tuple[list, dict]:
    patterns = []
    targets  = {}

    if len(df) < 30:
        return patterns, targets

    order = min(7, max(2, len(df)//10))

    try:
        idx_max = argrelextrema(df['High'].values, np.greater_equal, order=order)[0]
        idx_min = argrelextrema(df['Low'].values,  np.less_equal,    order=order)[0]
        p_max   = df['High'].iloc[idx_max].tail(6).tolist()
        p_min   = df['Low'].iloc[idx_min].tail(6).tolist()
        p_max_i = list(df.index[idx_max])[-6:]
        p_min_i = list(df.index[idx_min])[-6:]

        # ── BODENFORMATIONEN ──────────────────────────────────────
        if len(p_min) >= 2:
            b1, b2 = p_min[-2], p_min[-1]
            if b1 > 0 and abs(b1-b2)/b1 < 0.03:
                patterns.append("Doppelboden")
                try:
                    neckline = df['High'].loc[p_min_i[-2]:p_min_i[-1]].max()
                except Exception:
                    neckline = float(df['Close'].iloc[-1])
                depth = neckline - min(b1, b2)
                targets["Doppelboden_Nackenlinie"] = round(neckline, 2)
                targets["Doppelboden_Ziel_50%"]    = round(neckline + depth * 0.5, 2)
                targets["Doppelboden_Ziel_100%"]   = round(neckline + depth, 2)

        if len(p_min) >= 3:
            b1, b2, b3 = p_min[-3], p_min[-2], p_min[-1]
            spread = max(b1,b2,b3) - min(b1,b2,b3)
            if b1 > 0 and spread/b1 < 0.04:
                patterns.append("Dreifachboden")
                neckline = float(df['Close'].rolling(20).mean().iloc[-1])
                depth    = neckline - min(b1,b2,b3)
                targets["Dreifachboden_Ziel"] = round(neckline + depth, 2)

        if len(p_min) >= 3:
            ls, h, rs = p_min[-3], p_min[-2], p_min[-1]
            if h < ls and h < rs and ls > 0 and abs(ls-rs)/ls < 0.05:
                patterns.append("Umgekehrte SKS (Bodenformation)")
                try:
                    neckline = df['High'].iloc[idx_min[-3]:idx_min[-1]].max()
                    depth    = neckline - h
                    targets["Inv_SKS_Nackenlinie"] = round(neckline, 2)
                    targets["Inv_SKS_Ziel"]        = round(neckline + depth, 2)
                except Exception: pass

        rvol_v = float(df['RVOL'].iloc[-1]) if 'RVOL' in df.columns and pd.notna(df['RVOL'].iloc[-1]) else 0
        if df['Close'].iloc[-1] < df['Open'].iloc[-1] and rvol_v > 2.0:
            patterns.append("Selling Climax (Potenzielle Wende)")
            targets["Selling_Climax_Einstieg"] = round(float(df['High'].iloc[-1]), 2)

        if len(df) >= 10:
            recent_low  = float(df['Low'].tail(10).min())
            recent_high = float(df['High'].tail(3).max())
            if recent_low > 0 and (recent_high - recent_low) / recent_low > 0.05:
                patterns.append("V-Boden (Starker Rebound)")
                targets["V_Boden_Fortsetzung"] = round(recent_high * 1.05, 2)

        # ── TOPFORMATIONEN ────────────────────────────────────────
        if len(p_max) >= 2:
            t1, t2 = p_max[-2], p_max[-1]
            if t1 > 0 and abs(t1-t2)/t1 < 0.03:
                patterns.append("Doppeltop")
                try:
                    neckline = df['Low'].loc[p_max_i[-2]:p_max_i[-1]].min()
                except Exception:
                    neckline = float(df['Close'].iloc[-1]) * 0.95
                depth = max(t1,t2) - neckline
                targets["Doppeltop_Nackenlinie"] = round(neckline, 2)
                targets["Doppeltop_Ziel_50%"]    = round(neckline - depth * 0.5, 2)
                targets["Doppeltop_Ziel_100%"]   = round(neckline - depth, 2)

        if len(p_max) >= 3:
            ls, k, rs = p_max[-3], p_max[-2], p_max[-1]
            if k > ls and k > rs and ls > 0 and abs(ls-rs)/ls < 0.04:
                patterns.append("SKS-Formation (Topformation)")
                try:
                    neckline = df['Low'].iloc[idx_max[-3]:idx_max[-1]].min()
                    depth    = k - neckline
                    targets["SKS_Nackenlinie"] = round(neckline, 2)
                    targets["SKS_Ziel"]        = round(neckline - depth, 2)
                except Exception: pass

        if df['Close'].iloc[-1] > df['Open'].iloc[-1] and rvol_v > 2.5:
            patterns.append("Buying Climax (Erschöpfungsrally)")
            targets["Buying_Climax_SL"] = round(float(df['Low'].iloc[-1]), 2)

        # ── FIBONACCI (52W Swing) ─────────────────────────────────
        df_1y  = df.tail(252)
        high1y = float(df_1y['High'].max())
        low1y  = float(df_1y['Low'].min())
        swing  = high1y - low1y
        if swing > 0:
            targets["Fib_23.6%"] = round(low1y + swing * 0.236, 2)
            targets["Fib_38.2%"] = round(low1y + swing * 0.382, 2)
            targets["Fib_50.0%"] = round(low1y + swing * 0.500, 2)
            targets["Fib_61.8%"] = round(low1y + swing * 0.618, 2)
            targets["Fib_78.6%"] = round(low1y + swing * 0.786, 2)

        # ── GAP & BOLLINGER ───────────────────────────────────────
        if len(df) >= 2:
            prev    = float(df['Close'].iloc[-2])
            c_open  = float(df['Open'].iloc[-1])
            vol_a   = df['Volume'].rolling(20).mean().iloc[-2] if len(df)>=20 else df['Volume'].mean()
            gap     = (c_open - prev) / max(prev, 0.001)
            if gap > 0.015:
                patterns.append(f"{'Power ' if df['Volume'].iloc[-1] > vol_a*1.5 else ''}Gap Up (+{round(gap*100,1)}%)")
            elif gap < -0.015:
                patterns.append(f"{'Power ' if df['Volume'].iloc[-1] > vol_a*1.5 else ''}Gap Down ({round(gap*100,1)}%)")

        if all(c in df.columns for c in ['BB_Upper','BB_Lower','SMA200']):
            bw = (df['BB_Upper'] - df['BB_Lower']) / df['SMA200'].replace(0, np.nan)
            if len(bw.dropna()) >= 100:
                bw_min = bw.rolling(100).min().iloc[-1]
                if pd.notna(bw.iloc[-1]) and pd.notna(bw_min) and bw.iloc[-1] < bw_min * 1.1:
                    patterns.append("Bollinger Squeeze")

    except Exception as e:
        print(f"[pattern_detect] {e}")

    return patterns, targets
