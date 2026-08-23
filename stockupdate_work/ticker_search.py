# ticker_search.py — Name-zu-Ticker Suche mit robustem Fuzzy-Matching

import unicodedata
import re

# ── Normalisierung ──────────────────────────────────────────────────────────
def _norm(s: str) -> str:
    """Kleinbuchstaben, Umlaute normalisieren, Sonderzeichen entfernen."""
    s = s.lower().strip()
    # Umlaute → ASCII
    replacements = {
        'ä':'ae','ö':'oe','ü':'ue','ß':'ss',
        'é':'e','è':'e','ê':'e','ë':'e',
        'à':'a','â':'a','á':'a',
        'ñ':'n','ç':'c','ô':'o','î':'i','û':'u',
    }
    for ch, rep in replacements.items():
        s = s.replace(ch, rep)
    # Satzzeichen entfernen außer Punkt, Bindestrich
    s = re.sub(r"[&'\"]", '', s)
    return s

# ── Ticker → [Name, Aliases] ────────────────────────────────────────────────
TICKER_NAMES: dict[str, list[str]] = {
    # ── USA TECH ────────────────────────────────────────────────────────────
    "AAPL":   ["Apple"],
    "MSFT":   ["Microsoft"],
    "NVDA":   ["Nvidia"],
    "GOOGL":  ["Google", "Alphabet"],
    "GOOG":   ["Google C"],
    "META":   ["Meta", "Facebook"],
    "AMZN":   ["Amazon"],
    "TSLA":   ["Tesla"],
    "AVGO":   ["Broadcom"],
    "ORCL":   ["Oracle"],
    "ADBE":   ["Adobe"],
    "CRM":    ["Salesforce"],
    "AMD":    ["AMD", "Advanced Micro Devices"],
    "QCOM":   ["Qualcomm"],
    "TXN":    ["Texas Instruments"],
    "INTU":   ["Intuit"],
    "AMAT":   ["Applied Materials"],
    "LRCX":   ["Lam Research"],
    "KLAC":   ["KLA"],
    "SNPS":   ["Synopsys"],
    "CDNS":   ["Cadence"],
    "MCHP":   ["Microchip Technology"],
    "INTC":   ["Intel"],
    "IBM":    ["IBM"],
    "CSCO":   ["Cisco"],
    "ACN":    ["Accenture"],
    "FTNT":   ["Fortinet"],
    "PANW":   ["Palo Alto Networks"],
    "CRWD":   ["Crowdstrike"],
    "ZS":     ["Zscaler"],
    "DDOG":   ["Datadog"],
    "MU":     ["Micron"],
    "ANET":   ["Arista Networks"],
    "NET":    ["Cloudflare"],
    "SNOW":   ["Snowflake"],
    "MDB":    ["MongoDB"],
    "PLTR":   ["Palantir"],
    "NFLX":   ["Netflix"],
    "SQ":     ["Block", "Square"],
    "COIN":   ["Coinbase"],
    "HOOD":   ["Robinhood"],
    "SOFI":   ["SoFi"],
    "RIVN":   ["Rivian"],
    # ── USA FINANCIALS ──────────────────────────────────────────────────────
    "JPM":    ["JPMorgan", "JP Morgan"],
    "BAC":    ["Bank of America"],
    "WFC":    ["Wells Fargo"],
    "C":      ["Citigroup", "Citi"],
    "GS":     ["Goldman Sachs"],
    "MS":     ["Morgan Stanley"],
    "BLK":    ["BlackRock"],
    "SCHW":   ["Charles Schwab"],
    "AXP":    ["American Express", "Amex"],
    "V":      ["Visa"],
    "MA":     ["Mastercard"],
    "PYPL":   ["PayPal"],
    "COF":    ["Capital One"],
    "CME":    ["CME Group"],
    "SPGI":   ["S&P Global"],
    "MCO":    ["Moodys"],
    # ── USA HEALTHCARE ──────────────────────────────────────────────────────
    "JNJ":    ["Johnson Johnson", "J&J"],
    "LLY":    ["Eli Lilly", "Lilly"],
    "UNH":    ["UnitedHealth"],
    "ABBV":   ["AbbVie"],
    "MRK":    ["Merck US"],
    "PFE":    ["Pfizer"],
    "TMO":    ["Thermo Fisher"],
    "ABT":    ["Abbott"],
    "DHR":    ["Danaher"],
    "BMY":    ["Bristol Myers"],
    "AMGN":   ["Amgen"],
    "GILD":   ["Gilead"],
    "VRTX":   ["Vertex"],
    "REGN":   ["Regeneron"],
    "ISRG":   ["Intuitive Surgical"],
    "SYK":    ["Stryker"],
    "BSX":    ["Boston Scientific"],
    "MDT":    ["Medtronic"],
    "NVO":    ["Novo Nordisk US", "Ozempic"],
    # ── USA CONSUMER ────────────────────────────────────────────────────────
    "PG":     ["Procter Gamble", "P&G"],
    "KO":     ["Coca-Cola", "Coke"],
    "PEP":    ["PepsiCo", "Pepsi"],
    "WMT":    ["Walmart"],
    "COST":   ["Costco"],
    "HD":     ["Home Depot"],
    "MCD":    ["McDonalds"],
    "NKE":    ["Nike"],
    "LOW":    ["Lowes"],
    "SBUX":   ["Starbucks"],
    "BKNG":   ["Booking"],
    "MAR":    ["Marriott"],
    "HLT":    ["Hilton"],
    "PM":     ["Philip Morris"],
    "MO":     ["Altria"],
    "DIS":    ["Disney", "Walt Disney"],
    "CL":     ["Colgate"],
    "EL":     ["Estee Lauder"],
    # ── USA ENERGY ──────────────────────────────────────────────────────────
    "XOM":    ["Exxon", "ExxonMobil"],
    "CVX":    ["Chevron"],
    "COP":    ["ConocoPhillips", "Conoco"],
    "SLB":    ["Schlumberger"],
    "HAL":    ["Halliburton"],
    "OXY":    ["Occidental"],
    "PBR":    ["Petrobras"],
    "FCX":    ["Freeport McMoRan"],
    "NEM":    ["Newmont"],
    "GOLD":   ["Barrick Gold"],
    "LIN":    ["Linde"],
    # ── USA INDUSTRIALS ─────────────────────────────────────────────────────
    "GE":     ["General Electric"],
    "HON":    ["Honeywell"],
    "UPS":    ["UPS", "United Parcel Service"],
    "BA":     ["Boeing"],
    "LMT":    ["Lockheed Martin"],
    "RTX":    ["Raytheon"],
    "NOC":    ["Northrop Grumman"],
    "GD":     ["General Dynamics"],
    "CAT":    ["Caterpillar"],
    "DE":     ["John Deere", "Deere"],
    "FDX":    ["FedEx"],
    "MMM":    ["3M"],
    "VZ":     ["Verizon"],
    "DIS":    ["Disney"],
    # ── USA REITs ───────────────────────────────────────────────────────────
    "AMT":    ["American Tower"],
    "PLD":    ["Prologis"],
    "EQIX":   ["Equinix"],
    "PSA":    ["Public Storage"],
    "O":      ["Realty Income"],
    "DLR":    ["Digital Realty"],
    "SPG":    ["Simon Property"],
    # ── DEUTSCHLAND ─────────────────────────────────────────────────────────
    "ADS.DE":  ["Adidas"],
    "AIR.DE":  ["Airbus"],
    "ALV.DE":  ["Allianz"],
    "BAS.DE":  ["BASF"],
    "BAYN.DE": ["Bayer"],
    "BEI.DE":  ["Beiersdorf", "Nivea"],
    "BMW.DE":  ["BMW", "Bayerische Motoren Werke"],
    "CBK.DE":  ["Commerzbank"],
    "CON.DE":  ["Continental"],
    "DBK.DE":  ["Deutsche Bank"],
    "DB1.DE":  ["Deutsche Boerse", "Deutsche Börse"],
    "DHL.DE":  ["DHL", "Deutsche Post"],
    "DTE.DE":  ["Deutsche Telekom", "Telekom"],
    "EOAN.DE": ["EON", "E.ON"],
    "ENR.DE":  ["Siemens Energy"],
    "FRE.DE":  ["Fresenius"],
    "HEI.DE":  ["Heidelberg Materials", "HeidelbergCement"],
    "HEN3.DE": ["Henkel"],
    "IFX.DE":  ["Infineon"],
    "MBG.DE":  ["Mercedes", "Daimler"],
    "MRK.DE":  ["Merck KGaA", "Merck Darmstadt"],
    "MTX.DE":  ["MTU Aero", "MTU"],
    "MUV2.DE": ["Munich Re", "Muenchener Rueck", "Muenchen Re", "Münchener Rück"],
    "P911.DE": ["Porsche AG"],
    "PAH3.DE": ["Porsche SE", "Porsche Holding"],
    "PUM.DE":  ["Puma"],
    "RHM.DE":  ["Rheinmetall"],
    "RWE.DE":  ["RWE"],
    "SAP.DE":  ["SAP"],
    "SRT3.DE": ["Sartorius"],
    "SHL.DE":  ["Siemens Healthineers"],
    "SIE.DE":  ["Siemens"],
    "SY1.DE":  ["Symrise"],
    "TKA.DE":  ["ThyssenKrupp", "Thyssenkrupp"],
    "VNA.DE":  ["Vonovia"],
    "VOW3.DE": ["Volkswagen", "VW"],
    "ZAL.DE":  ["Zalando"],
    "BNR.DE":  ["Brenntag"],
    "BOSS.DE": ["Hugo Boss", "Boss"],
    "BVB.DE":  ["Borussia Dortmund", "BVB"],
    "HLAG.DE": ["Hapag-Lloyd"],
    "HOT.DE":  ["Hochtief"],
    "IFX.DE":  ["Infineon"],
    "LEG.DE":  ["LEG Immobilien"],
    "NDX1.DE": ["Nordex"],
    "PBB.DE":  ["Pfandbriefbank", "Deutsche Pfandbriefbank"],
    "SDF.DE":  ["K+S", "Kali und Salz"],
    "TAG.DE":  ["TAG Immobilien"],
    "TTK.DE":  ["TeamViewer"],
    "VAR1.DE": ["Varta"],
    "BC8.DE":  ["Bechtle"],
    "EVD.DE":  ["CTS Eventim"],
    "FRA.DE":  ["Fraport"],
    "GFT.DE":  ["GFT Technologies"],
    # ── FRANKREICH ──────────────────────────────────────────────────────────
    "AI.PA":   ["Air Liquide"],
    "AIR.PA":  ["Airbus FR"],
    "CS.PA":   ["AXA"],
    "BN.PA":   ["Danone"],
    "DSY.PA":  ["Dassault Systemes"],
    "ENGI.PA": ["Engie", "GDF Suez"],
    "EL.PA":   ["EssilorLuxottica", "Essilor"],
    "RMS.PA":  ["Hermes", "Hermès"],
    "KER.PA":  ["Kering", "Gucci", "Balenciaga"],
    "OR.PA":   ["LOreal", "L'Oreal"],
    "MC.PA":   ["LVMH", "Louis Vuitton"],
    "RI.PA":   ["Pernod Ricard"],
    "SAF.PA":  ["Safran"],
    "SGO.PA":  ["Saint-Gobain"],
    "SAN.PA":  ["Sanofi"],
    "SU.PA":   ["Schneider Electric"],
    "GLE.PA":  ["Societe Generale"],
    "TTE.PA":  ["TotalEnergies", "Total"],
    "DG.PA":   ["Vinci"],
    "BNP.PA":  ["BNP Paribas", "BNP"],
    "ACA.PA":  ["Credit Agricole"],
    "VIE.PA":  ["Veolia"],
    "ML.PA":   ["Michelin"],
    "STLA.PA": ["Stellantis", "Fiat", "Peugeot"],
    "RNO.PA":  ["Renault"],
    "CA.PA":   ["Carrefour"],
    # ── SPANIEN ─────────────────────────────────────────────────────────────
    "SAN.MC":  ["Santander"],
    "BBVA.MC": ["BBVA"],
    "IBE.MC":  ["Iberdrola"],
    "ITX.MC":  ["Inditex", "Zara"],
    "TEF.MC":  ["Telefonica"],
    "REP.MC":  ["Repsol"],
    "CABK.MC": ["CaixaBank"],
    "CLNX.MC": ["Cellnex"],
    "AMS.MC":  ["Amadeus"],
    # ── ITALIEN ─────────────────────────────────────────────────────────────
    "ENEL.MI": ["Enel"],
    "ENI.MI":  ["Eni"],
    "RACE.MI": ["Ferrari"],
    "UCG.MI":  ["UniCredit"],
    "ISP.MI":  ["Intesa Sanpaolo", "Intesa"],
    "G.MI":    ["Generali"],
    "STM.MI":  ["STMicroelectronics", "ST Micro"],
    "MONC.MI": ["Moncler"],
    "LDO.MI":  ["Leonardo"],
    # ── NIEDERLANDE ─────────────────────────────────────────────────────────
    "ASML.AS": ["ASML"],
    "ADYEN.AS":["Adyen"],
    "AD.AS":   ["Ahold Delhaize", "Albert Heijn"],
    "INGA.AS": ["ING"],
    "HEIA.AS": ["Heineken"],
    "UMG.AS":  ["Universal Music"],
    "PHIA.AS": ["Philips"],
    "AKZA.AS": ["Akzo Nobel"],
    # ── SCHWEIZ ─────────────────────────────────────────────────────────────
    "NESN.SW": ["Nestle", "Nestlé"],
    "ROG.SW":  ["Roche"],
    "NOVN.SW": ["Novartis"],
    "ABBN.SW": ["ABB"],
    "CFR.SW":  ["Richemont", "Cartier"],
    "SIKA.SW": ["Sika"],
    "UBSG.SW": ["UBS"],
    "ZURN.SW": ["Zurich Insurance", "Zurich"],
    "HOLN.SW": ["Holcim"],
    "LINDT.SW":["Lindt"],
    # ── UK ──────────────────────────────────────────────────────────────────
    "AZN.L":   ["AstraZeneca", "Astra Zeneca"],
    "HSBA.L":  ["HSBC"],
    "ULVR.L":  ["Unilever"],
    "GSK.L":   ["GSK", "GlaxoSmithKline", "Glaxo"],
    "RIO.L":   ["Rio Tinto"],
    "BP.L":    ["BP"],
    "SHEL.L":  ["Shell"],
    "BATS.L":  ["British American Tobacco", "BAT"],
    "DGE.L":   ["Diageo"],
    "LLOY.L":  ["Lloyds"],
    "BARC.L":  ["Barclays"],
    "NWG.L":   ["NatWest"],
    "RR.L":    ["Rolls-Royce", "Rolls Royce"],
    "BA.L":    ["BAE Systems"],
    "GLEN.L":  ["Glencore"],
    "AAL.L":   ["Anglo American"],
    "NEXT.L":  ["Next"],
    "MKS.L":   ["Marks Spencer", "M&S"],
    "TSCO.L":  ["Tesco"],
    # ── SKANDINAVIEN ────────────────────────────────────────────────────────
    "NOVO-B.CO":   ["Novo Nordisk", "Ozempic", "Wegovy"],
    "CARL-B.CO":   ["Carlsberg"],
    "MAERSK-B.CO": ["Maersk"],
    "ORSTED.CO":   ["Orsted"],
    "EQNR":        ["Equinor", "Statoil"],
    "VOLV-B.ST":   ["Volvo"],
    "ERIC-B.ST":   ["Ericsson"],
    "ASSA-B.ST":   ["Assa Abloy"],
    "KNEBV.HE":    ["Kone"],
    "NESTE.HE":    ["Neste"],
    # ── CHINA / HONG KONG ───────────────────────────────────────────────────
    "BABA":    ["Alibaba"],
    "TCEHY":   ["Tencent OTC"],
    "JD":      ["JD.com"],
    "BIDU":    ["Baidu"],
    "PDD":     ["Pinduoduo", "Temu"],
    "NIO":     ["NIO"],
    "XPEV":    ["Xpeng"],
    "LI":      ["Li Auto"],
    "0700.HK": ["Tencent", "Tencent HK"],
    "9988.HK": ["Alibaba HK"],
    "9618.HK": ["JD.com HK"],
    "9888.HK": ["Baidu HK"],
    "0939.HK": ["CCB", "China Construction Bank", "China Bau Bank"],
    "1398.HK": ["ICBC", "Industrial Commercial Bank"],
    "3988.HK": ["Bank of China"],
    "0941.HK": ["China Mobile"],
    "0728.HK": ["China Telecom"],
    "0762.HK": ["China Unicom"],
    "2628.HK": ["China Life Insurance"],
    "0386.HK": ["Sinopec"],
    "0857.HK": ["PetroChina"],
    "0992.HK": ["Lenovo"],
    "0175.HK": ["Geely"],
    "9868.HK": ["Xpeng HK"],
    "2015.HK": ["Li Auto HK"],
    # ── SÜDKOREA ────────────────────────────────────────────────────────────
    "005930.KS": ["Samsung", "Samsung Electronics"],
    "000660.KS": ["SK Hynix", "Hynix"],
    "005380.KS": ["Hyundai Motor", "Hyundai"],
    "000270.KS": ["Kia", "Kia Motors"],
    "005490.KS": ["POSCO"],
    "051910.KS": ["LG Chem"],
    "006400.KS": ["Samsung SDI"],
    "035420.KS": ["Naver"],
    "035720.KS": ["Kakao"],
    "066570.KS": ["LG Electronics"],
    "003550.KS": ["LG Corp"],
    "017670.KS": ["SK Telecom"],
    "030200.KS": ["KT Corporation"],
    "015760.KS": ["KEPCO", "Korea Electric Power"],
    "247540.KS": ["Ecopro BM"],
    "086790.KS": ["Hana Financial", "Hana Bank"],
    "105560.KS": ["KB Financial", "KB Kookmin"],
    "055550.KS": ["Shinhan Financial", "Shinhan Bank"],
    "011070.KS": ["LG Innotek"],
    # ── JAPAN ───────────────────────────────────────────────────────────────
    "7203.T":  ["Toyota"],
    "6758.T":  ["Sony"],
    "9984.T":  ["SoftBank"],
    "6861.T":  ["Keyence"],
    "8306.T":  ["Mitsubishi UFJ", "MUFG"],
    "9432.T":  ["NTT"],
    "6367.T":  ["Daikin"],
    "6501.T":  ["Hitachi"],
    "9433.T":  ["KDDI"],
    "8035.T":  ["Tokyo Electron"],
    "7751.T":  ["Canon"],
    "7267.T":  ["Honda"],
    "6702.T":  ["Fujitsu"],
    "4063.T":  ["Shin-Etsu Chemical"],
    "9983.T":  ["Fast Retailing", "Uniqlo"],
    "2914.T":  ["Japan Tobacco"],
    "7974.T":  ["Nintendo"],
    "4661.T":  ["Oriental Land", "Tokyo Disney"],
    "6954.T":  ["Fanuc"],
    "5108.T":  ["Bridgestone"],
    "3382.T":  ["Seven Eleven"],
    "2502.T":  ["Asahi"],
    "4901.T":  ["Fujifilm"],
    # ── EMERGING MARKETS ────────────────────────────────────────────────────
    "INFY":   ["Infosys"],
    "HDB":    ["HDFC Bank"],
    "IBN":    ["ICICI Bank"],
    "TTM":    ["Tata Motors"],
    "VALE":   ["Vale"],
    "ITUB":   ["Itau Unibanco"],
    "ABEV":   ["Ambev"],
    "KEP":    ["KEPCO ADR"],
    "KT":     ["KT Corp ADR"],
}


def _tokenize(s: str) -> list[str]:
    """Splittet einen String in Tokens und normalisiert."""
    n = _norm(s)
    # Split auf Leerzeichen, Bindestrich, Punkt
    tokens = re.split(r'[\s\-\.]+', n)
    return [t for t in tokens if t]


def search_ticker(query: str, all_tickers: list[str], max_results: int = 12) -> list[str]:
    """
    Sucht Ticker nach Name oder Symbol.
    Gibt sortierte Liste von Labels zurück: "ALV.DE — Allianz"
    
    Unterstützt:
    - Exakter Ticker: "ALV.DE"
    - Ticker-Präfix: "ALV"
    - Name exakt: "Allianz"
    - Token-Start: "ali" → matcht "Allianz" (Token beginnt mit "ali")
    - Token-Enthalt: "ianz" → matcht "Allianz"
    - Multi-Token: "deutsche bank" → beide Tokens müssen matchen
    - Sonderzeichen: "münch" → matcht "Muenchen" / "München"
    """
    q = query.strip()
    if not q:
        return []

    q_norm   = _norm(q)
    q_tokens = _tokenize(q)

    if not q_tokens:
        return []

    results: list[tuple[int, str, str]] = []  # (priority, ticker, label)

    for ticker in all_tickers:
        t_lower  = ticker.lower()
        t_norm   = _norm(ticker)
        names    = TICKER_NAMES.get(ticker, [])
        best_prio = None
        best_name = names[0] if names else ticker

        # ── Ticker-Matching ─────────────────────────────────────
        # Prio 0: exakter Ticker-Match
        if t_lower == q.lower():
            best_prio = 0
        # Prio 1: Ticker beginnt mit Query
        elif t_norm.startswith(q_norm) or t_lower.startswith(q.lower()):
            best_prio = 1
        # Prio 6: Query irgendwo im Ticker
        elif q_norm in t_norm:
            best_prio = 6

        # ── Name-Matching ────────────────────────────────────────
        for name in names:
            name_norm   = _norm(name)
            name_tokens = _tokenize(name)

            # Prio 2: exakter Name-Match
            if name_norm == q_norm:
                if best_prio is None or best_prio > 2:
                    best_prio = 2; best_name = name
                break

            # Prio 3: Name beginnt mit Query
            if name_norm.startswith(q_norm):
                if best_prio is None or best_prio > 3:
                    best_prio = 3; best_name = name
                continue

            # Prio 4: Alle Query-Tokens matchen Token-Anfänge im Namen
            # "ali" matches "Allianz" weil token "allianz" starts with "ali"
            # "deut ban" matches "Deutsche Bank"
            all_match = True
            for qt in q_tokens:
                tok_match = any(nt.startswith(qt) for nt in name_tokens)
                if not tok_match:
                    all_match = False
                    break
            if all_match:
                if best_prio is None or best_prio > 4:
                    best_prio = 4; best_name = name
                continue

            # Prio 5: Query-String irgendwo im Namen enthalten
            if q_norm in name_norm:
                if best_prio is None or best_prio > 5:
                    best_prio = 5; best_name = name

        if best_prio is not None:
            label = f"{ticker} — {best_name}" if best_name != ticker else ticker
            results.append((best_prio, ticker, label))

    results.sort(key=lambda x: (x[0], x[1]))
    return [r[2] for r in results[:max_results]]


def label_to_ticker(label: str) -> str:
    """Extrahiert den Ticker aus 'ALV.DE — Allianz' → 'ALV.DE'"""
    return label.split(" — ")[0].strip()


def get_display_name(ticker: str) -> str:
    """'ALV.DE' → 'ALV.DE — Allianz'"""
    names = TICKER_NAMES.get(ticker, [])
    return f"{ticker} — {names[0]}" if names else ticker
