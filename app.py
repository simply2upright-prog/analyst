# app.py — v4: Zeitraum-Wahl, historische Marker, Volume-of-Interest, Einstiegssignale

import streamlit as st
import pandas as pd
import numpy as np
import base64
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from database import get_all_tickers, get_tickers_by_group, get_all_groups, get_currency, get_ticker_count
from engine import (get_analysis, send_mail_report, classify_signal,
                    get_futures_analysis, FUTURES_TICKERS,
                    get_all_futures_groups, get_futures_by_group)
from detail_engine import get_detail_analysis, compute_hit_rate
from ticker_search import search_ticker, label_to_ticker, get_display_name

APP_URL = "https://stockupdate-65qjxum6gq2gpjpr5exqfd.streamlit.app"

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="In8Invest Scanner", page_icon="📊", layout="wide")

try:
    def _b64(p):
        with open(p,"rb") as f: return base64.b64encode(f.read()).decode()
    st.markdown(f'<div style="margin-bottom:8px"><img src="data:image/png;base64,{_b64("Icon in8invest.png")}" width="160"></div>',
                unsafe_allow_html=True)
except: pass

st.title("📊 Strategie Scanner")
st.caption(f"🌍 Datenbank: {get_ticker_count()} Ticker · {len(get_all_groups())} Märkte & Sektoren")

# ─── QUERY PARAMS — Deep-Link aus Email (?ticker=XXX) ─────────────────────────
params         = st.query_params
deep_link_ticker = params.get("ticker", None)

# ─── SESSION STATE ─────────────────────────────────────────────────────────────
if "results"    not in st.session_state: st.session_state.results    = pd.DataFrame()
if "det_ticker" not in st.session_state: st.session_state.det_ticker = deep_link_ticker or ""

# Wenn Deep-Link vorhanden, direkt Tab 2 aktiv machen
default_tab = 1 if deep_link_ticker else 0  # 0-indexed

# ─── HELPER: Ampel-Badge ──────────────────────────────────────────────────────
def _sig_badge(sig: dict) -> str:
    return (f"<span style='background:{sig['color']};color:#fff;padding:3px 10px;"
            f"border-radius:12px;font-size:12px;font-weight:700'>{sig['emoji']} {sig['label']}</span>")

def _ind_badge(v, low, high, fmt="{:.3f}", invert=False) -> str:
    if v is None: return "<span style='color:#888'>N/A</span>"
    try:
        fv = float(v)
        if fv <= low:    c,t = ("#1a9e3f","OS") if not invert else ("#c0392b","OB")
        elif fv >= high: c,t = ("#c0392b","OB") if not invert else ("#1a9e3f","OS")
        else:             c,t = "#7f8c8d","—"
        b = f"<span style='background:{c};color:#fff;padding:1px 6px;border-radius:3px;font-size:11px;font-weight:700'>{t}</span>"
        return f"{b} {fmt.format(fv)}"
    except: return str(v)

def _fnum(v, fmt="{:.2f}", suffix="") -> str:
    """Sicheres Zahlenformat - zeigt 'N/A' statt Crash/„nan“ bei fehlenden Werten."""
    if v is None: return "N/A"
    try:
        fv = float(v)
        if not np.isfinite(fv): return "N/A"
        return f"{fmt.format(fv)}{suffix}"
    except Exception:
        return "N/A"

def _macd_badge(turn) -> str:
    if turn == "up":   return "<span style='background:#0d7a2e;color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:700'>DREHT ↑ (Trigger)</span>"
    if turn == "down": return "<span style='background:#8e1f14;color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:700'>DREHT ↓ (Trigger)</span>"
    return "<span style='background:#7f8c8d;color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:700'>KEINE UMKEHR</span>"

# ─── TABS ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🚀 Scanner", "📊 Detail-Analyse", "📐 Formations-Check",
    "🛢️ Rohstoffe & Futures", "📅 Automation"
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — SCANNER
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.header("Globaler Markt-Scanner")
    c1, c2 = st.columns([4, 1])
    sel_grp   = c1.selectbox("📂 Markt / Index / Sektor:", ["🌍 Alle Gruppen"] + get_all_groups(), key="scan_grp")
    min_score = c2.selectbox("Min. Score:", [1, 2, 3, 4])

    if st.button("🔥 SCAN STARTEN"):
        tickers = get_all_tickers() if sel_grp == "🌍 Alle Gruppen" else get_tickers_by_group(sel_grp)
        raw, prog, stat = [], st.progress(0), st.empty()
        for i, t in enumerate(tickers):
            stat.text(f"Scanne {i+1}/{len(tickers)}: {t}")
            res = get_analysis(t)
            if res: raw.append(res)
            prog.progress((i+1)/len(tickers))
        df = pd.DataFrame(raw)
        if not df.empty:
            df = df[df["Score"] >= min_score].sort_values("Score", ascending=False).reset_index(drop=True)
            st.session_state.results = df
            stat.success(f"✅ {len(df)} Signale in {len(tickers)} Titeln.")
        else:
            stat.warning("Keine Signale.")

    if not st.session_state.results.empty:
        df_show = st.session_state.results.copy()
        st.markdown("##### Ergebnisse — 🟢 OVERSOLD · 🔴 OVERBOUGHT · ⚪ NEUTRAL")

        def _row_html(r):
            sv, sf, ss, cv = r.get('StochRSI'), r.get('Stoch_Fast'), r.get('Stoch_Slow'), r.get('CCI')
            macd_turn = r.get('MACD_Turn')
            sig  = classify_signal(sv, sf, ss, cv, macd_turn)
            sc   = int(r.get('Score', 0))
            sc_c = {4:"#0d7a2e",3:"#1a9e3f",2:"#f39c12",1:"#7f8c8d"}.get(sc,"#999")
            return (f"<tr>"
                    f"<td><b>{r['Ticker']}</b></td><td>{r.get('Name','')}</td>"
                    f"<td>{_sig_badge(sig)}</td>"
                    f"<td style='text-align:right'><b>{r.get('Preis','')}</b></td>"
                    f"<td style='text-align:center'>{_ind_badge(sv,0.15,0.85)}</td>"
                    f"<td style='text-align:center'>{_ind_badge(sf,20,80,'{:.1f}')}</td>"
                    f"<td style='text-align:center'>{_ind_badge(ss,25,75,'{:.1f}')}</td>"
                    f"<td style='text-align:center'>{_ind_badge(cv,-100,100,'{:.1f}',invert=True)}</td>"
                    f"<td style='text-align:center;font-size:11px'>{_macd_badge(macd_turn)}</td>"
                    f"<td style='text-align:center'><span style='background:{sc_c};color:#fff;"
                    f"padding:2px 8px;border-radius:10px;font-weight:700'>{sc}/4</span></td>"
                    f"<td>{r.get('Div','')}</td><td>{r.get('KGV','')}</td>"
                    f"</tr>")

        thead = """<thead style='background:#1e2235;color:#8892a4;font-size:11px;text-transform:uppercase;letter-spacing:.5px'>
          <tr><th style='padding:10px 8px'>Ticker</th><th>Name</th><th>Signal</th><th>Preis</th>
          <th>StochRSI</th><th>Stoch F</th><th>Stoch S</th><th>CCI</th><th>MACD</th>
          <th>Score</th><th>Div</th><th>KGV</th></tr></thead>"""
        tbody = "".join(_row_html(r) for _, r in df_show.iterrows())
        st.markdown(
            f"<div style='overflow-x:auto'><table style='border-collapse:collapse;width:100%;"
            f"font-size:13px;font-family:sans-serif'>{thead}<tbody>{tbody}</tbody></table></div>",
            unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — DETAIL-ANALYSE
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.header("Analyse & Chart-Center")

    all_t = get_all_tickers()

    # ── Suchfeld mit Name-Suche ─────────────────────────────────────────────
    # Deep-Link aus Email: ?ticker=ALV.DE
    if deep_link_ticker and deep_link_ticker in all_t:
        if "search_query" not in st.session_state:
            st.session_state["search_query"] = get_display_name(deep_link_ticker)

    search_q = st.text_input(
        "🔍 Aktie suchen (Name, Ticker, Alias):",
        value=st.session_state.get("search_query", ""),
        placeholder="z.B. Allianz, Samsung, 0700.HK, Tencent, NVDA …",
        key="search_input",
    )
    st.session_state["search_query"] = search_q

    # Suchergebnisse filtern
    if search_q.strip():
        suggestions = search_ticker(search_q, all_t, max_results=12)
    else:
        suggestions = [get_display_name(t) for t in all_t[:20]]

    if not suggestions:
        st.warning(f"Keine Treffer für **{search_q}** — bitte Ticker direkt eingeben (z.B. ALV.DE)")
        suggestions = [get_display_name(t) for t in all_t[:5]]

    sel_label = st.selectbox("Ergebnisse:", suggestions, key="det_t_label")
    sel_t = label_to_ticker(sel_label)

    # Zeitraum-Auswahl — Standard 6 Monate
    tf_opts  = {"3 Monate": 63, "6 Monate": 126, "1 Jahr": 252, "2 Jahre": 504}
    sel_tf   = st.radio("Zeitraum:", list(tf_opts.keys()), index=1, horizontal=True, key="det_tf")
    tf_bars  = tf_opts[sel_tf]

    if sel_t:
        with st.spinner(f"Lade {sel_t} …"):
            data = get_detail_analysis(sel_t)

        if data and "df" in data:
            cur = data["Währung"]
            sig = data["Sig_Data"]
            sc_col = "green" if data["Score"]>=2 else ("orange" if data["Score"]==1 else "red")

            # ── Kompakter Header: Name, Signal, alle Kern-Kennzahlen in einer Zeile ──
            col_h1, col_h2 = st.columns([3,1])
            col_h1.markdown(f"### {data['Name']} ({sel_t})")
            col_h2.markdown(
                f"{_sig_badge(sig)} &nbsp; :{sc_col}[**Score {data['Score']}/4**]",
                unsafe_allow_html=True)

            c1,c2,c3,c4,c5,c6 = st.columns(6)
            c1.metric("Kurs", f"{_fnum(data['Preis'])} {cur}",
                      delta=f"{_fnum(data['Perf_Abs'])} ({_fnum(data['Perf_Pct'])}%)")
            c2.metric("52W Hoch", f"{_fnum(data['Hoch_365'])} {cur}")
            c3.metric("52W Tief", f"{_fnum(data['Tief_365'])} {cur}")
            c4.metric("Dividende", data["Div"])
            c5.metric("KGV", str(data["KGV"]))
            c6.metric("RVOL", f"{_fnum(data['RVOL'])}x")

            # ── Indikator-Status: alle 4 Strategie-Kriterien kompakt in einer Zeile ──
            st.divider()
            st.markdown("#### Indikator-Status — die 4 Kriterien deiner Strategie")
            ib1,ib2,ib3,ib4 = st.columns(4)
            ib1.markdown(f"**StochRSI(70)** &nbsp; {_ind_badge(data['StochRSI'],0.15,0.85)}", unsafe_allow_html=True)
            ib2.markdown(
                f"**Stoch F/S** &nbsp; {_ind_badge(data.get('Stoch_Fast'),20,80,'{:.1f}')} / "
                f"{_ind_badge(data.get('Stoch_Slow'),25,75,'{:.1f}')}",
                unsafe_allow_html=True)
            ib3.markdown(f"**CCI(20)** &nbsp; {_ind_badge(data['CCI'],-100,100,'{:.1f}',invert=True)}", unsafe_allow_html=True)
            ib4.markdown(f"**MACD(70,200,9)** &nbsp; {_macd_badge(data.get('MACD_Turn'))}", unsafe_allow_html=True)
            st.markdown(f"<span style='color:#888;font-size:12px'>Z-Score: {_ind_badge(data['Z_Score'],-1.5,1.5,'{:.2f}')}</span>", unsafe_allow_html=True)

            # ── HAUPT-CHART (6 Panels) ─────────────────────────────
            df_full = data["df"]
            df_p    = df_full.tail(tf_bars)
            targets = data.get("Targets", {})
            sig_history = data.get("Signal_History", [])
            entry_sigs  = data.get("Entry_Signals", [])

            fig = make_subplots(
                rows=7, cols=1, shared_xaxes=True, vertical_spacing=0.02,
                row_heights=[0.30, 0.10, 0.115, 0.115, 0.115, 0.115, 0.14],
                subplot_titles=("Kurs + Bollinger + Marker", "Volume of Interest",
                                "Stochastik (Fast/Slow)", "StochRSI (70)",
                                "CCI (20)", "Z-Score", "MACD (70,200,9) — Trigger"),
            )

            # Panel 1: Kurs + Bollinger
            fig.add_trace(go.Scatter(x=df_p.index, y=df_p["BB_Lower"], name="BB–",
                line=dict(color="#00eeee",width=.8,dash="dot"), showlegend=False), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_p.index, y=df_p["BB_Upper"], name="Bollinger Band",
                fill="tonexty", fillcolor="rgba(0,238,238,0.05)",
                line=dict(color="#00eeee",width=.8,dash="dot")), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_p.index, y=df_p["SMA200"], name="EMA200",
                line=dict(color="#666",width=1.5,dash="dash")), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_p.index, y=df_p["Close"], name="Kurs",
                line=dict(color="#facc15",width=2.5)), row=1, col=1)

            # ── Historische Signal-Marker (blaue Punkte) ──────────
            sig_in_range = [s for s in sig_history if s["date"] in df_p.index or
                            (len(df_p)>0 and s["date"] >= df_p.index[0])]
            if sig_in_range:
                fig.add_trace(go.Scatter(
                    x=[s["date"] for s in sig_in_range],
                    y=[s["price"] for s in sig_in_range],
                    mode="markers",
                    name="Signal-Treffer",
                    marker=dict(color="#3b82f6", size=10, symbol="circle",
                                line=dict(color="#ffffff", width=2)),
                    hovertemplate="<b>%{x|%d.%m.%Y}</b><br>Preis: %{y:.2f}<br>Signal-Cluster<extra></extra>",
                ), row=1, col=1)

            # ── Einstiegssignale (grüne Dreiecke) ─────────────────
            entry_in_range = [e for e in entry_sigs if
                              len(df_p)>0 and e["entry_date"] >= df_p.index[0]]
            if entry_in_range:
                fig.add_trace(go.Scatter(
                    x=[e["entry_date"] for e in entry_in_range],
                    y=[e["entry_price"] for e in entry_in_range],
                    mode="markers+text",
                    name="Einstieg",
                    text=["▲" for _ in entry_in_range],
                    textposition="bottom center",
                    textfont=dict(color="#4ade80", size=14),
                    marker=dict(color="#4ade80", size=12, symbol="triangle-up",
                                line=dict(color="#ffffff", width=1.5)),
                    hovertemplate=(
                        "<b>Einstieg %{x|%d.%m.%Y}</b><br>"
                        "Preis: %{y:.2f}<br>"
                        "Vorlauf: " + "<br>".join([f"{e['days_to_entry']}d nach Signal" for e in entry_in_range]) +
                        "<extra></extra>"
                    ),
                ), row=1, col=1)

            # ── Fibonacci & Zielkurs-Linien ────────────────────────
            fib_colors = {"Fib_23.6%":"#fbbf24","Fib_38.2%":"#f97316",
                          "Fib_50.0%":"#ef4444","Fib_61.8%":"#ec4899","Fib_78.6%":"#a855f7"}
            for k,v in targets.items():
                if k.startswith("Fib_"):
                    fc = fib_colors.get(k,"#aaa")
                    fig.add_hline(y=v, line_dash="dot", line_color=fc, line_width=1,
                                  annotation_text=f" {k} {v:.2f} ",
                                  annotation_font=dict(color=fc,size=10),
                                  annotation_position="right", row=1, col=1)
                elif "Nackenlinie" in k or "Ziel" in k or "Einstieg" in k:
                    is_buy   = "Doppelboden" in k or "Inv_SKS" in k or "Einstieg" in k or "V_Boden" in k
                    lc       = "#4ade80" if is_buy else "#f87171"
                    fig.add_hline(y=v, line_dash="dash", line_color=lc, line_width=1.5,
                                  annotation_text=f" {k.replace('_',' ')} {v:.2f} ",
                                  annotation_font=dict(color=lc,size=10),
                                  annotation_position="right", row=1, col=1)

            # Panel 2: Volume of Interest (horizontal Balken am Kurs)
            # Wir berechnen ein Preis-Volumen-Histogramm und zeigen es als Scatter
            close_vals = df_p["Close"].values
            vol_vals   = df_p["Volume"].values
            if len(close_vals) > 5:
                n_bins  = 40
                lo, hi  = close_vals.min(), close_vals.max()
                if hi > lo:
                    bins    = np.linspace(lo, hi, n_bins + 1)
                    bw      = bins[1] - bins[0]
                    centers = (bins[:-1] + bins[1:]) / 2
                    vol_sum = np.zeros(n_bins)
                    for price_v, vol_v in zip(close_vals, vol_vals):
                        idx = min(int((price_v - lo) / bw), n_bins - 1)
                        vol_sum[idx] += vol_v
                    # POC = Price of Control (höchstes Volumen)
                    poc_idx   = int(np.argmax(vol_sum))
                    poc_price = centers[poc_idx]

                    # Volumen normalisieren auf 0–100 für Darstellung
                    vol_norm = vol_sum / vol_sum.max() * 100 if vol_sum.max() > 0 else vol_sum

                    # Im Volume-Panel als Candlestick-artige Balken
                    bar_cols = ["#1a9e3f" if c == poc_price else
                                ("#4ade80" if v > np.percentile(vol_sum, 75) else "#334155")
                                for c, v in zip(centers, vol_sum)]

                    fig.add_trace(go.Bar(
                        x=vol_norm, y=centers,
                        orientation="h",
                        name="Volume of Interest",
                        marker_color=bar_cols,
                        opacity=0.85,
                        hovertemplate="Preis: %{y:.2f}<br>Vol-Index: %{x:.1f}<extra></extra>",
                    ), row=2, col=1)

                    # POC Linie im Kurs-Panel
                    fig.add_hline(y=poc_price, line_color="#22c55e", line_width=2, line_dash="solid",
                                  annotation_text=f" 🎯 POC {poc_price:.2f} ",
                                  annotation_font=dict(color="#22c55e",size=11,family="Arial Black"),
                                  annotation_bgcolor="rgba(34,197,94,0.15)",
                                  annotation_position="left", row=1, col=1)

            # Panel 3: Stochastik
            fig.add_trace(go.Scatter(x=df_p.index, y=df_p["Stoch_Fast"], name="Stoch Fast",
                line=dict(color="#00ffff",width=1.2)), row=3, col=1)
            fig.add_trace(go.Scatter(x=df_p.index, y=df_p["Stoch_Slow"], name="Stoch Slow",
                line=dict(color="#ff00ff",width=2)), row=3, col=1)
            for y,c in [(10,"#4ade80"),(90,"#f87171")]:
                fig.add_hline(y=y, line_color=c, line_width=1, line_dash="dot", row=3, col=1)

            # Panel 4: StochRSI
            fig.add_trace(go.Scatter(x=df_p.index, y=df_p["StochRSI_70"], name="StochRSI",
                line=dict(color="#fff",width=1.5)), row=4, col=1)
            # Oversold-Bereich grün füllen
            fig.add_trace(go.Scatter(
                x=df_p.index, y=np.where(df_p["StochRSI_70"]<0.1, df_p["StochRSI_70"], 0.1),
                fill="tozeroy", fillcolor="rgba(74,222,128,0.15)",
                line=dict(width=0), showlegend=False, name="OS-Zone"), row=4, col=1)
            for y,c in [(0.1,"#4ade80"),(0.9,"#f87171")]:
                fig.add_hline(y=y, line_color=c, line_dash="dot", row=4, col=1)

            # Panel 5: CCI
            cci_vals = df_p["CCI_20"].fillna(0)
            cci_colors = ["#f87171" if v > 100 else "#4ade80" if v < -100 else "#94a3b8"
                          for v in cci_vals]
            fig.add_trace(go.Bar(x=df_p.index, y=cci_vals, name="CCI",
                marker_color=cci_colors, opacity=0.7), row=5, col=1)
            for y,c in [(-100,"#4ade80"),(100,"#f87171")]:
                fig.add_hline(y=y, line_color=c, line_width=1.5, row=5, col=1)

            # Panel 6: Z-Score
            z_vals = df_p["Z_Score"].fillna(0)
            z_colors = ["#f87171" if v > 2 else "#4ade80" if v < -2 else
                        "#fbbf24" if v < -1 else "#94a3b8" for v in z_vals]
            fig.add_trace(go.Bar(x=df_p.index, y=z_vals, name="Z-Score",
                marker_color=z_colors, opacity=0.75), row=6, col=1)
            for y,c in [(-2,"#4ade80"),(-1,"#86efac"),(0,"#475569"),(1,"#fca5a5"),(2,"#f87171")]:
                fig.add_hline(y=y, line_color=c, line_width=1, line_dash="dot", row=6, col=1)

            # Panel 7: MACD — Linie/Signal + Histogramm, plus Marker für erkannte Umkehrpunkte
            macd_vals   = df_p["MACD"]
            signal_vals = df_p["SIGNAL"]
            hist_vals   = df_p["OSMA"].fillna(0)
            hist_colors = ["#4ade80" if v >= 0 else "#f87171" for v in hist_vals]
            fig.add_trace(go.Bar(x=df_p.index, y=hist_vals, name="OSMA (Histogramm)",
                marker_color=hist_colors, opacity=0.6), row=7, col=1)
            fig.add_trace(go.Scatter(x=df_p.index, y=macd_vals, name="MACD",
                line=dict(color="#38bdf8", width=1.5)), row=7, col=1)
            fig.add_trace(go.Scatter(x=df_p.index, y=signal_vals, name="Signal",
                line=dict(color="#c084fc", width=1.5)), row=7, col=1)
            fig.add_hline(y=0, line_color="#475569", line_width=1, row=7, col=1)

            fig.update_layout(
                height=1300, template="plotly_dark",
                paper_bgcolor="#0e1117", plot_bgcolor="#161b22",
                margin=dict(l=10,r=140,t=40,b=10),
                hovermode="x unified", showlegend=True,
                legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
            )
            fig.update_xaxes(showgrid=True, gridcolor="#1e2235", zeroline=False)
            fig.update_yaxes(showgrid=True, gridcolor="#1e2235", zeroline=False)
            # Volume-of-Interest x-Achse ausblenden
            fig.update_xaxes(showticklabels=False, row=2, col=1)

            st.plotly_chart(fig, use_container_width=True)

            # ── Trefferquoten-Analyse — direkt nach dem Chart, das ist die
            #    wichtigste Kennzahl: "hat dieses Signal historisch funktioniert?" ──
            if entry_sigs:
                st.divider()
                st.markdown("#### 🎯 Trefferquoten-Analyse: Hat der Boden gehalten?")
                st.caption(f"{len(entry_sigs)} unabhängige historische Trades · prüft ob nach jedem Einstieg "
                           f"innerhalb von 40 Tagen eine Trendwende (+5% oder +10%) stattgefunden hat.")

                hr = compute_hit_rate(entry_sigs, df_full, forward_days=40)

                if hr["total"] > 0:
                    rate_pct = hr["rate"] * 100
                    # Farbige Gesamtbewertung
                    if rate_pct >= 65:
                        rate_color = "#1a9e3f"
                        rate_label = "🟢 Zuverlässiges Signal"
                    elif rate_pct >= 45:
                        rate_color = "#f39c12"
                        rate_label = "🟡 Mittelmäßig zuverlässig"
                    else:
                        rate_color = "#c0392b"
                        rate_label = "🔴 Wenig zuverlässig"

                    # Gauge + Metriken
                    hc1, hc2 = st.columns([1, 2])
                    with hc1:
                        pass  # go already imported
                        fig_hr = go.Figure(go.Indicator(
                            mode="gauge+number",
                            value=rate_pct,
                            number={"suffix": "%", "font": {"size": 48, "color": rate_color, "family": "Arial Black"}},
                            title={"text": f"Trefferquote<br><span style='font-size:13px;color:{rate_color}'>{rate_label}</span>",
                                   "font": {"size": 15, "color": "white"}},
                            gauge={
                                "axis": {"range": [0, 100]},
                                "bar":  {"color": rate_color},
                                "bgcolor": "#161b22",
                                "steps": [
                                    {"range": [0, 45],  "color": "#2d1b1b"},
                                    {"range": [45, 65], "color": "#2d2a1b"},
                                    {"range": [65, 100],"color": "#1b2d1b"},
                                ],
                                "threshold": {"line": {"color": "white", "width": 3}, "value": 65},
                            }
                        ))
                        fig_hr.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={"color": "white"}, height=280)
                        st.plotly_chart(fig_hr, use_container_width=True)

                    with hc2:
                        hm1, hm2, hm3 = st.columns(3)
                        hm1.metric("Analysierte Signale", hr["total"])
                        hm2.metric("✅ Trendwenden", hr["hits"],
                                   delta=f"+{hr['hits']}", delta_color="normal")
                        hm3.metric("❌ Kein Boden", hr["misses"],
                                   delta=f"-{hr['misses']}", delta_color="inverse")

                        # Detailtabelle mit Farbmarkierung
                        if hr["details"]:
                            row_colors = {
                                "strong":   "#1a4d2e",   # dunkelgrün
                                "weak":     "#4d3d00",   # dunkelgelb
                                "fail":     "#4d1a1a",   # dunkelrot
                                "sideways": "#2d2d2d",   # grau
                                "new":      "#1a2d4d",   # dunkelblau
                            }
                            rows_html = ""
                            for d in hr["details"]:
                                rc  = d.get("result_code", "sideways")
                                bg  = row_colors.get(rc, "#222")
                                mg  = d.get("max_gain_pct")
                                ml  = d.get("max_loss_pct")
                                mg_str = f"+{mg:.1f}%" if mg is not None else "–"
                                ml_str = f"{ml:.1f}%" if ml is not None else "–"
                                date_str = d["entry_date"].strftime("%d.%m.%Y") if hasattr(d["entry_date"],"strftime") else str(d["entry_date"])
                                rows_html += (
                                    f"<tr style='background:{bg}'>"
                                    f"<td style='padding:7px 10px;color:#ccc'>{date_str}</td>"
                                    f"<td style='padding:7px 10px;color:#ccc;text-align:right'>{d['entry_price']:.2f} {cur}</td>"
                                    f"<td style='padding:7px 10px;font-weight:700;color:#{'4ade80' if 'strong' in rc else 'fbbf24' if 'weak' in rc else 'f87171' if 'fail' in rc else '94a3b8'}'>{d['result']}</td>"
                                    f"<td style='padding:7px 10px;color:#4ade80;text-align:right'>{mg_str}</td>"
                                    f"<td style='padding:7px 10px;color:#f87171;text-align:right'>{ml_str}</td>"
                                    f"</tr>"
                                )
                            st.markdown(
                                f"<div style='overflow-x:auto'>"
                                f"<table style='border-collapse:collapse;width:100%;font-size:12px;font-family:sans-serif'>"
                                f"<thead><tr style='background:#1e2235;color:#8892a4;font-size:10px;text-transform:uppercase'>"
                                f"<th style='padding:8px 10px'>Einstieg</th>"
                                f"<th style='padding:8px 10px;text-align:right'>Preis</th>"
                                f"<th style='padding:8px 10px'>Ergebnis</th>"
                                f"<th style='padding:8px 10px;text-align:right'>Max Gewinn</th>"
                                f"<th style='padding:8px 10px;text-align:right'>Max Verlust</th>"
                                f"</tr></thead><tbody>{rows_html}</tbody></table></div>",
                                unsafe_allow_html=True
                            )
            else:
                st.info("Noch keine historischen Einstiegssignale im gewählten Datenzeitraum erkennbar.")

            # ── Einstiegszeitpunkte im Detail (aufklappbar) ─────────
            if entry_sigs:
                with st.expander(f"📋 {len(entry_sigs)} historische Einstiegssignale im Detail", expanded=False):
                    st.caption("Trigger 'MACD' = Histogramm hat gedreht (eigentliches Kaufsignal deiner Strategie). "
                               "Trigger 'Preis' = MACD hat im Fenster nicht gedreht, Kurs hat sich aber "
                               "bereits +2% über dem lokalen Tief stabilisiert (Ersatzkriterium).")
                    entry_rows = []
                    for e in entry_sigs[-12:]:
                        sd = e["signal_date"].strftime("%d.%m.%Y") if hasattr(e["signal_date"],"strftime") else str(e["signal_date"])
                        ed = e["entry_date"].strftime("%d.%m.%Y")  if hasattr(e["entry_date"],"strftime")  else str(e["entry_date"])
                        entry_rows.append({
                            "Signal-Datum":   sd,
                            "Signal-Preis":   f"{e['signal_price']:.2f} {cur}",
                            "Trigger":        e.get("trigger", "–"),
                            "Einstieg-Datum": ed,
                            "Einstieg-Preis": f"{e['entry_price']:.2f} {cur}",
                            "Vorlauf":        f"{e['days_to_entry']} Tage",
                        })
                    if entry_rows:
                        e_df = pd.DataFrame(entry_rows)
                        st.dataframe(e_df, hide_index=True, use_container_width=True)
                        avg_days = round(np.mean([e["days_to_entry"] for e in entry_sigs]), 1)
                        avg_up   = round(np.mean([e["upside_pct"]    for e in entry_sigs]), 1)
                        ei1,ei2,ei3 = st.columns(3)
                        ei1.metric("Ø Vorlauf Signal→Einstieg", f"{avg_days} Tage")
                        ei2.metric("Ø Bestätigungs-Anstieg",    f"+{avg_up}%")
                        ei3.metric("Einstieg-Signale gesamt",   len(entry_sigs))

            # ── Historische Signal-Treffer (roh, vor Deduplizierung) ─
            if sig_history:
                with st.expander(f"📅 {len(sig_history)} historische Rohtreffer der Extremwert-Kriterien (Zeitraum: {sel_tf})", expanded=False):
                    sig_df = pd.DataFrame([
                        {
                            "Datum":     s["date"].strftime("%d.%m.%Y") if hasattr(s["date"],"strftime") else str(s["date"]),
                            "Preis":     f"{s['price']:.2f} {cur}",
                            "StochRSI":  s["StochRSI"],
                            "CCI":       s["CCI"],
                            "MACD":      s.get("MACD_Turn") or "–",
                            "Score":     f"{s['score']}/4",
                        } for s in sig_history
                    ])
                    st.dataframe(sig_df, hide_index=True, use_container_width=True)

            # ── Muster & Targets ──────────────────────────────────
            if data.get("Patterns"):
                st.markdown("#### 📐 Erkannte Muster")
                for p in data["Patterns"]: st.info(f"📌 {p}")

            if data.get("Targets"):
                st.markdown("#### 🎯 Zielkurse & Fibonacci")
                price_now = data["Preis"]
                fib_keys  = [k for k in targets if k.startswith("Fib_")]
                other_keys= [k for k in targets if not k.startswith("Fib_")]

                if fib_keys:
                    st.markdown("**Fibonacci Retracement (52W Swing)**")
                    cols_f = st.columns(len(fib_keys))
                    for j,(k) in enumerate(fib_keys):
                        v   = targets[k]
                        pct = round((v-price_now)/price_now*100,1) if price_now else 0
                        cols_f[j].metric(k.replace("_"," "), f"{v:.2f} {cur}", f"{pct:+.1f}%")

                if other_keys:
                    st.markdown("**Formation-Ziele**")
                    cols_o = [other_keys[i:i+3] for i in range(0,len(other_keys),3)]
                    for row_k in cols_o:
                        cols_r = st.columns(3)
                        for j,k in enumerate(row_k):
                            v   = targets[k]
                            pct = round((v-price_now)/price_now*100,1) if price_now else 0
                            arrow = "🎯" if pct > 0 else "⚠️"
                            cols_r[j].metric(f"{arrow} {k.replace('_',' ')}", f"{v:.2f} {cur}", f"{pct:+.1f}%")

        else:
            st.error(f"❌ Keine Daten für **{sel_t}**. Bitte Symbol prüfen oder anderen Zeitraum wählen.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — FORMATIONS-CHECK
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.header("📐 Formations-Check: Boden & Topbildung")
    mode = st.radio("Modus:", ["🔍 Markt scannen", "🎯 Einzelne Aktie"], horizontal=True)

    if mode == "🔍 Markt scannen":
        grp_opts  = ["🌍 Alle Gruppen"] + get_all_groups()
        grp_t3    = st.selectbox("Gruppe:", grp_opts, key="form_grp")
        scan_mode = st.radio("Suche nach:",
            ["🟢 Bodenbildung (Kaufchancen)", "🔴 Topbildung (Verkaufchancen)", "🔍 Alle Signale"],
            horizontal=True)

        if st.button("🚀 Formations-Scan starten"):
            tickers_t3 = get_all_tickers() if grp_t3=="🌍 Alle Gruppen" else get_tickers_by_group(grp_t3)
            result_list, prog, txt = [], st.progress(0), st.empty()

            for i,t in enumerate(tickers_t3):
                txt.text(f"Scanne: {t}")
                res = get_detail_analysis(t)
                if res:
                    patterns = res.get("Patterns", [])
                    targets  = res.get("Targets",  {})
                    entries  = res.get("Entry_Signals", [])

                    b_score = t_score = 0
                    if res["Z_Score"] < -1.5: b_score += 15
                    if res["Z_Score"] < -2.0: b_score += 15
                    if res["RVOL"]    > 1.3:  b_score += 10
                    if res["RVOL"]    > 2.0:  b_score += 15
                    for p in patterns:
                        if "Selling Climax" in p:  b_score += 30
                        if "Doppelboden"    in p:  b_score += 20
                        if "Dreifachboden"  in p:  b_score += 25
                        if "Umgekehrte SKS" in p:  b_score += 25
                        if "V-Boden"        in p:  b_score += 15

                    if res["Z_Score"] > 1.5: t_score += 15
                    if res["Z_Score"] > 2.0: t_score += 15
                    if res["RVOL"]    > 2.0: t_score += 15
                    for p in patterns:
                        if "Buying Climax" in p:   t_score += 30
                        if "Doppeltop"     in p:   t_score += 20
                        if "SKS-Formation" in p:   t_score += 25

                    b_score = min(b_score, 100)
                    t_score = min(t_score, 100)

                    show = (("Bodenbildung" in scan_mode and b_score >= 30) or
                            ("Topbildung"   in scan_mode and t_score >= 30) or
                            ("Alle"         in scan_mode and (b_score >= 30 or t_score >= 30)))

                    if show:
                        # Einstiegs-Info
                        avg_entry = ""
                        if entries:
                            avg_days = round(np.mean([e["days_to_entry"] for e in entries]), 0)
                            avg_entry = f"Ø {int(avg_days)}d Vorlauf"

                        # Bestes Ziel
                        entry_target = ""
                        if b_score >= t_score:
                            if "Doppelboden_Nackenlinie" in targets:
                                entry_target = f"↑ Neckline {targets['Doppelboden_Nackenlinie']} → Ziel {targets.get('Doppelboden_Ziel_100%','?')}"
                        else:
                            if "Doppeltop_Nackenlinie" in targets:
                                entry_target = f"↓ Neckline {targets['Doppeltop_Nackenlinie']} → Ziel {targets.get('Doppeltop_Ziel_100%','?')}"

                        result_list.append({
                            "Ticker":        t,
                            "Name":          res["Name"],
                            "Signal":        res["Signal"],
                            "Boden %":       b_score,
                            "Top %":         t_score,
                            "Muster":        " | ".join(patterns[:3]) if patterns else "–",
                            "Einstieg-Info": avg_entry or "–",
                            "Ziel":          entry_target or "–",
                            "Preis":         f"{res['Preis']} {res['Währung']}",
                            "Z-Score":       res["Z_Score"],
                            "RVOL":          res["RVOL"],
                        })
                prog.progress((i+1)/len(tickers_t3))

            txt.empty()
            if result_list:
                sort_col = "Boden %" if "Top" not in scan_mode else "Top %"
                df_f     = pd.DataFrame(result_list).sort_values(sort_col, ascending=False)
                st.subheader(f"🔥 {len(df_f)} Formationen erkannt")
                st.dataframe(df_f, hide_index=True, use_container_width=True)
            else:
                st.warning("Keine Formationen gefunden.")

    else:
        sq3 = st.text_input("🔍 Aktie suchen:", placeholder="z.B. Porsche, Ferrari, Toyota …", key="form_search")
        all_t3 = get_all_tickers()
        sugg3  = search_ticker(sq3, all_t3, 10) if sq3.strip() else [get_display_name(t) for t in all_t3[:10]]
        if not sugg3: sugg3 = [get_display_name(t) for t in all_t3[:5]]
        lbl3   = st.selectbox("Ergebnisse:", sugg3, key="form_single_lbl")
        sel_t3 = label_to_ticker(lbl3)
        if sel_t3:
            with st.spinner(f"Analysiere {sel_t3} …"):
                data = get_detail_analysis(sel_t3)

            if data and "df" in data:
                cur      = data["Währung"]
                patterns = data.get("Patterns", [])
                targets  = data.get("Targets", {})
                entries  = data.get("Entry_Signals", [])

                b_score = t_score = 0
                b_reasons = []; t_reasons = []
                if data["Z_Score"] < -2.0: b_score += 30; b_reasons.append(f"📏 Z-Score {data['Z_Score']:.2f}")
                elif data["Z_Score"] < -1.5: b_score += 15
                if data["RVOL"]    > 2.0:  b_score += 25; b_reasons.append(f"📊 RVOL {data['RVOL']:.2f}x")
                elif data["RVOL"]  > 1.3:  b_score += 10
                for p in patterns:
                    if "Selling Climax" in p: b_score += 30; b_reasons.append("🚨 Selling Climax")
                    if "Doppelboden"    in p: b_score += 20; b_reasons.append("📐 Doppelboden")
                    if "Dreifachboden"  in p: b_score += 25; b_reasons.append("📐 Dreifachboden")
                    if "Umgekehrte SKS" in p: b_score += 25; b_reasons.append("📐 Inverse SKS")
                    if "V-Boden"        in p: b_score += 15; b_reasons.append("📐 V-Boden")
                if data["Z_Score"] > 2.0:  t_score += 30; t_reasons.append(f"📏 Z-Score {data['Z_Score']:.2f}")
                elif data["Z_Score"] > 1.5:t_score += 15
                if data["RVOL"]    > 2.0:  t_score += 15; t_reasons.append(f"📊 RVOL {data['RVOL']:.2f}x")
                for p in patterns:
                    if "Buying Climax" in p: t_score += 30; t_reasons.append("🚨 Buying Climax")
                    if "Doppeltop"     in p: t_score += 20; t_reasons.append("📐 Doppeltop")
                    if "SKS-Formation" in p: t_score += 25; t_reasons.append("📐 SKS")
                b_score = min(b_score, 100)
                t_score = min(t_score, 100)

                col_b, col_t = st.columns(2)
                for col, score, label, color, reasons, emoji in [
                    (col_b, b_score, "Bodenbildung", "#1a9e3f", b_reasons, "🟢"),
                    (col_t, t_score, "Topbildung",   "#c0392b", t_reasons, "🔴"),
                ]:
                    with col:
                        fig_g = go.Figure(go.Indicator(
                            mode="gauge+number", value=score,
                            number={"suffix":"%","font":{"size":56,"color":color,"family":"Arial Black"}},
                            title={"text":f"{emoji} {label}","font":{"size":17,"color":"white"}},
                            gauge={"axis":{"range":[0,100]},"bar":{"color":color},
                                   "bgcolor":"#161b22",
                                   "steps":[{"range":[0,40],"color":"#252840"},{"range":[40,70],"color":"#333650"}],
                                   "threshold":{"line":{"color":"#fff","width":3},"value":70}}))
                        fig_g.update_layout(paper_bgcolor="rgba(0,0,0,0)",font={"color":"white"},height=320)
                        st.plotly_chart(fig_g, use_container_width=True)
                        for r in reasons: st.write(f"✅ {r}")
                        if   score >= 70: st.success(f"🔥 STARKES {label.upper()}-SIGNAL!")
                        elif score >= 40: st.warning(f"⚠️ {label} möglich")
                        else:             st.info(f"Kein klares Signal")

                # Einstiegszeitpunkte
                st.divider()
                if entries:
                    st.subheader(f"🎯 Einstiegssignal-Historie ({len(entries)} Treffer)")
                    avg_days = round(np.mean([e["days_to_entry"] for e in entries]), 1)
                    avg_up   = round(np.mean([e["upside_pct"]    for e in entries]), 1)
                    ea,eb,ec = st.columns(3)
                    ea.metric("Ø Vorlauf", f"{avg_days} Tage", help="Tage zwischen Signal und +2%-Bestätigung")
                    eb.metric("Ø Bestätigungs-%", f"+{avg_up}%")
                    ec.metric("Treffer gesamt", len(entries))

                    entry_df = pd.DataFrame([{
                        "Signal":    e["signal_date"].strftime("%d.%m.%Y") if hasattr(e["signal_date"],"strftime") else str(e["signal_date"]),
                        "Sig-Preis": f"{e['signal_price']:.2f}",
                        "Lok. Tief": f"{e['local_low']:.2f}",
                        "Einstieg":  e["entry_date"].strftime("%d.%m.%Y")  if hasattr(e["entry_date"],"strftime")  else str(e["entry_date"]),
                        "E-Preis":   f"{e['entry_price']:.2f}",
                        "Vorlauf":   f"{e['days_to_entry']}d",
                        "+%":        f"+{e['upside_pct']:.1f}%",
                    } for e in entries])
                    st.dataframe(entry_df, hide_index=True, use_container_width=True)

                # Ziele
                if targets:
                    st.divider()
                    st.subheader("🎯 Zielkurse")
                    price_now = data["Preis"]
                    n = 4
                    all_k = list(targets.keys())
                    for chunk in [all_k[i:i+n] for i in range(0,len(all_k),n)]:
                        cols_z = st.columns(n)
                        for j,k in enumerate(chunk):
                            v   = targets[k]
                            pct = round((v-price_now)/price_now*100,1) if price_now else 0
                            cols_z[j].metric(k.replace("_"," "), f"{v:.2f} {cur}", f"{pct:+.1f}%")

                # POC Chart
                st.divider()
                st.subheader("📊 Volume Profile (POC)")
                df_vp = data["df"].tail(252)
                counts, edges = np.histogram(df_vp["Close"], bins=50)
                centers  = (edges[:-1]+edges[1:])/2
                poc_price = centers[np.argmax(counts)]
                fig_vp = go.Figure()
                fig_vp.add_trace(go.Bar(y=centers, x=counts, orientation="h",
                    marker=dict(color=counts, colorscale="Blues", showscale=False)))
                fig_vp.add_hline(y=poc_price, line_dash="solid", line_color="#22c55e", line_width=4,
                    annotation_text=f" 🎯 POC {poc_price:.2f} {cur} ",
                    annotation_font=dict(color="white",size=16,family="Arial Black"),
                    annotation_bgcolor="#22c55e", annotation_position="bottom left")
                fig_vp.add_hline(y=data["Preis"], line_dash="dash", line_color="#facc15", line_width=4,
                    annotation_text=f" 💵 {data['Preis']} {cur} ",
                    annotation_font=dict(color="black",size=16,family="Arial Black"),
                    annotation_bgcolor="#facc15", annotation_position="top right")
                fig_vp.update_layout(template="plotly_dark",height=600,
                    paper_bgcolor="#0e1117",plot_bgcolor="#161b22",
                    xaxis=dict(title="Handelsintensität",showgrid=False),
                    yaxis=dict(title=f"Preis ({cur})",showgrid=True,gridcolor="#2d333b"))
                st.plotly_chart(fig_vp, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — ROHSTOFFE & FUTURES
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.header("🛢️ Rohstoffe, Energie & Futures")
    st.caption("Futures via Yahoo Finance. Preise in USD sofern nicht anders angegeben.")

    all_fg   = ["🌍 Alle Gruppen"] + get_all_futures_groups()
    sel_fg   = st.selectbox("Gruppe:", all_fg, key="fut_grp")
    fut_mode = st.radio("Ansicht:", ["📊 Übersicht / Scanner", "📈 Detail-Chart"], horizontal=True)

    if fut_mode == "📊 Übersicht / Scanner":
        if st.button("🔥 Futures Scan starten"):
            tickers_f = list(FUTURES_TICKERS.keys()) if sel_fg=="🌍 Alle Gruppen" else get_futures_by_group(sel_fg)
            fut_data, prog_f, stat_f = [], st.progress(0), st.empty()
            for i,t in enumerate(tickers_f):
                stat_f.text(f"Lade: {t}")
                res = get_futures_analysis(t)
                if res:
                    fut_data.append({
                        "Ticker":   t, "Name": res["Name"], "Gruppe": res["Gruppe"],
                        "Signal":   res["Signal"],
                        "Preis":    f"{res['Preis']} {res['Einheit']}",
                        "52W H":    res["52W_Hoch"], "52W T": res["52W_Tief"],
                        "1W %":     f"{res['Perf_1W']:+.1f}%" if res['Perf_1W'] else "–",
                        "1M %":     f"{res['Perf_1M']:+.1f}%" if res['Perf_1M'] else "–",
                        "RSI":      res["RSI"], "StochRSI": res["StochRSI"],
                        "CCI":      res["CCI"], "Score":    res["Score"],
                    })
                prog_f.progress((i+1)/len(tickers_f))
            stat_f.empty()
            if fut_data:
                df_f = pd.DataFrame(fut_data).sort_values("Score", ascending=False)

                def _frow(r):
                    sv,cv = r.get('StochRSI'),r.get('CCI')
                    sig   = classify_signal(sv, None, None, cv)
                    sc    = int(r.get('Score',0))
                    sc_c  = {4:"#1a9e3f",3:"#27ae60",2:"#f39c12",1:"#7f8c8d"}.get(sc,"#999")
                    pw = r.get('1W %','–'); pm = r.get('1M %','–')
                    pwc = "#1a9e3f" if pw and pw.startswith('+') else "#c0392b" if pw and pw.startswith('-') else "#888"
                    pmc = "#1a9e3f" if pm and pm.startswith('+') else "#c0392b" if pm and pm.startswith('-') else "#888"
                    return (f"<tr>"
                            f"<td><b>{r['Ticker']}</b></td><td>{r['Name']}</td>"
                            f"<td><span style='background:#2d3250;color:#a0aec0;padding:2px 8px;"
                            f"border-radius:6px;font-size:11px'>{r['Gruppe']}</span></td>"
                            f"<td>{_sig_badge(sig)}</td>"
                            f"<td style='text-align:right;font-weight:700'>{r['Preis']}</td>"
                            f"<td style='color:{pwc};text-align:center;font-weight:700'>{pw}</td>"
                            f"<td style='color:{pmc};text-align:center;font-weight:700'>{pm}</td>"
                            f"<td style='text-align:center'>{_ind_badge(r.get('RSI'),35,65,'{:.1f}')}</td>"
                            f"<td style='text-align:center'>{_ind_badge(sv,0.2,0.8)}</td>"
                            f"<td style='text-align:center'>{_ind_badge(cv,-80,80,'{:.1f}',invert=True)}</td>"
                            f"<td style='text-align:center'><span style='background:{sc_c};color:#fff;"
                            f"padding:2px 8px;border-radius:10px;font-weight:700'>{sc}/4</span></td>"
                            f"</tr>")

                thead_f = """<thead style='background:#1e2235;color:#8892a4;font-size:11px;text-transform:uppercase'>
                  <tr><th style='padding:10px 8px'>Ticker</th><th>Name</th><th>Gruppe</th><th>Signal</th>
                  <th>Preis</th><th>1W</th><th>1M</th><th>RSI</th><th>StochRSI</th><th>CCI</th><th>Score</th></tr>
                </thead>"""
                tbody_f = "".join(_frow(r) for _,r in df_f.iterrows())
                st.markdown(
                    f"<div style='overflow-x:auto'><table style='border-collapse:collapse;width:100%;"
                    f"font-size:13px;font-family:sans-serif'>{thead_f}<tbody>{tbody_f}</tbody></table></div>",
                    unsafe_allow_html=True)

    else:
        fut_options = {f"{v['name']} ({k})": k for k,v in FUTURES_TICKERS.items()}
        sel_fut_label = st.selectbox("Futures-Kontrakt:", list(fut_options.keys()), key="fut_det")
        sel_fut = fut_options[sel_fut_label]

        with st.spinner(f"Lade {sel_fut} …"):
            fdata = get_futures_analysis(sel_fut)

        if fdata and "df" in fdata:
            sig_f = fdata["Sig_Data"]
            unit  = fdata["Einheit"]
            fc1,fc2,fc3,fc4,fc5 = st.columns(5)
            fc1.markdown(_sig_badge(sig_f), unsafe_allow_html=True)
            fc2.metric("Preis", f"{fdata['Preis']} {unit}")
            fc3.metric("52W Hoch", f"{fdata['52W_Hoch']} {unit}")
            fc4.metric("52W Tief", f"{fdata['52W_Tief']} {unit}")
            fc5.metric("Score", f"{fdata['Score']}/4")

            fi1,fi2,fi3,fi4 = st.columns(4)
            fi1.markdown(f"**RSI** {_ind_badge(fdata['RSI'],35,65,'{:.1f}')}", unsafe_allow_html=True)
            fi2.markdown(f"**StochRSI** {_ind_badge(fdata['StochRSI'],0.2,0.8)}", unsafe_allow_html=True)
            fi3.markdown(f"**CCI** {_ind_badge(fdata['CCI'],-80,80,'{:.1f}',invert=True)}", unsafe_allow_html=True)
            fi4.markdown(f"**RVOL** <span style='font-size:14px'>{fdata['RVOL']}x</span>", unsafe_allow_html=True)

            dfp = fdata["df"]
            fig_fut = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.03,
                row_heights=[0.45,0.18,0.18,0.18],
                subplot_titles=("Kurs & Bollinger","Volumen","RSI","CCI"))
            fig_fut.add_trace(go.Scatter(x=dfp.index,y=dfp["BB_Lower"],name="BB-",line=dict(color="#00eeee",width=.8,dash="dot"),showlegend=False),row=1,col=1)
            fig_fut.add_trace(go.Scatter(x=dfp.index,y=dfp["BB_Upper"],name="Bollinger",fill="tonexty",fillcolor="rgba(0,238,238,0.05)",line=dict(color="#00eeee",width=.8,dash="dot")),row=1,col=1)
            fig_fut.add_trace(go.Scatter(x=dfp.index,y=dfp["EMA50"],name="EMA50",line=dict(color="#888",width=1.5,dash="dash")),row=1,col=1)
            fig_fut.add_trace(go.Scatter(x=dfp.index,y=dfp["Close"],name="Preis",line=dict(color="#facc15",width=2.5)),row=1,col=1)
            vc = ["#ff4444" if r["Open"]>r["Close"] else "#00cc66" for _,r in dfp.iterrows()]
            fig_fut.add_trace(go.Bar(x=dfp.index,y=dfp["Volume"],name="Vol",marker_color=vc,opacity=.7),row=2,col=1)
            fig_fut.add_trace(go.Scatter(x=dfp.index,y=dfp["RSI"],name="RSI",line=dict(color="#00ffff",width=1.5)),row=3,col=1)
            for y,c in [(30,"#4ade80"),(70,"#f87171")]: fig_fut.add_hline(y=y,line_color=c,line_width=1,row=3,col=1)
            fig_fut.add_trace(go.Scatter(x=dfp.index,y=dfp["CCI"],name="CCI",line=dict(color="#be94ff",width=2)),row=4,col=1)
            for y,c in [(-100,"#4ade80"),(100,"#f87171")]: fig_fut.add_hline(y=y,line_color=c,row=4,col=1)
            fig_fut.update_layout(height=900,template="plotly_dark",paper_bgcolor="black",plot_bgcolor="black",
                margin=dict(l=10,r=10,t=40,b=10),hovermode="x unified")
            fig_fut.update_xaxes(showgrid=True,gridcolor="#222")
            fig_fut.update_yaxes(showgrid=True,gridcolor="#222")
            st.plotly_chart(fig_fut, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — AUTOMATION
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.header("📅 Bericht-Versand & Automation")
    st.info("Der tägliche Report läuft automatisch via **GitHub Actions** (06:24 UTC). Hier manueller Trigger.")
    if st.button("📧 Report jetzt senden"):
        if not st.session_state.results.empty:
            try:
                pw = st.secrets["DAILY_EMAIL_PASS"]
                st.success(send_mail_report(st.session_state.results, pw))
            except Exception as e:
                st.error(f"Fehler: {e}")
        else:
            st.warning("⚠️ Erst Tab 1 Scanner ausführen.")
