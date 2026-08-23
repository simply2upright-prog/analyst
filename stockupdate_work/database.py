# database.py — Globale Aktien-Datenbank v2.0
# Abdeckung: USA (S&P500, NASDAQ, Dow Jones, Russell) | UK (FTSE100)
# China (A/H-Shares, HK, ADR) | Südkorea (KOSPI) | Japan (Nikkei)
# Deutschland (DAX/MDAX/SDAX) | Frankreich (CAC40) | Spanien (IBEX35)
# Italien (FTSE MIB) | Niederlande (AEX) | Schweiz (SMI)
# Skandinavien | Sektoren: Energy, Mining, Healthcare, Financials,
# Tech, Consumer, REIT, Utilities, Sin-Stocks, Emerging Markets

TICKER_LISTS = {

    # ═══════════════════════════════════════════════════════
    # USA — S&P 500 nach Sektoren
    # ═══════════════════════════════════════════════════════
    "SP500_TECH": [
        "AAPL", "MSFT", "NVDA", "GOOGL", "GOOG", "META", "AVGO",
        "ORCL", "ADBE", "CRM", "AMD", "QCOM", "TXN", "INTU", "AMAT",
        "LRCX", "KLAC", "SNPS", "CDNS", "MCHP", "INTC", "IBM",
        "CSCO", "ACN", "FTNT", "PANW", "CRWD", "ZS", "DDOG", "MU",
        "SMCI", "VRT", "ANET", "NET", "OKTA", "SNOW", "MDB", "PLTR",
    ],
    "SP500_FINANCIALS": [
        "JPM", "BAC", "WFC", "C", "GS", "MS", "BLK", "SCHW",
        "AXP", "V", "MA", "PYPL", "COF", "USB", "PNC", "TFC",
        "BK", "STT", "FITB", "KEY", "RF", "HBAN",
        "AFL", "MET", "PRU", "ALL", "AIG", "CB", "PGR", "TRV",
        "CME", "ICE", "NDAQ", "SPGI", "MCO",
    ],
    "SP500_HEALTHCARE": [
        "JNJ", "LLY", "UNH", "ABBV", "MRK", "PFE", "TMO", "ABT",
        "DHR", "BMY", "AMGN", "GILD", "VRTX", "REGN", "BIIB",
        "SYK", "BSX", "MDT", "BDX", "EW", "ISRG", "ZBH",
        "HCA", "CI", "CVS", "MCK", "ABC", "CAH", "IDXX",
        "IQV", "ILMN", "A", "WAT",
    ],
    "SP500_CONSUMER_STAPLES": [
        "PG", "KO", "PEP", "WMT", "COST", "MDLZ", "PM", "MO",
        "KHC", "GIS", "K", "CPB", "HRL", "CAG", "MKC",
        "CL", "CHD", "CLX", "EL", "KR", "DLTR", "DG",
    ],
    "SP500_CONSUMER_DISC": [
        "AMZN", "TSLA", "HD", "MCD", "NKE", "LOW", "SBUX", "TJX",
        "BKNG", "MAR", "HLT", "YUM", "CMG", "DPZ", "QSR",
        "F", "GM", "PHM", "DHI", "LEN", "NVR", "TOL",
        "ROST", "RL", "PVH", "EBAY", "ETSY", "RH", "WSM",
    ],
    "SP500_ENERGY": [
        "XOM", "CVX", "COP", "EOG", "SLB", "HAL", "MPC", "PSX",
        "VLO", "DVN", "FANG", "APA", "CTRA", "OXY", "PBR",
        "MRO", "HES", "BKR", "NOV", "CHRD", "MTDR", "PR", "SM",
    ],
    "SP500_INDUSTRIALS": [
        "GE", "HON", "UPS", "BA", "LMT", "RTX", "NOC", "GD",
        "CAT", "DE", "EMR", "ETN", "ITW", "PH", "IR", "ROK",
        "AME", "FTV", "XYL", "IDEX", "ROP",
        "UNP", "CSX", "NSC", "FDX", "PCAR", "GWW",
    ],
    "SP500_MATERIALS": [
        "LIN", "APD", "ECL", "SHW", "PPG", "NEM", "FCX", "NUE",
        "STLD", "AA", "CF", "MOS", "DOW", "LYB",
        "ALB", "MP", "CTVA", "FMC", "IFF", "AVY", "PKG",
    ],
    "SP500_UTILITIES": [
        "NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "PCG",
        "AWK", "WEC", "ES", "FE", "CNP", "AES", "NRG", "ETR",
        "EIX", "PPL", "DTE", "AEE", "CMS", "LNT",
    ],
    "SP500_REITS": [
        "AMT", "PLD", "CCI", "EQIX", "PSA", "O", "DLR", "VICI",
        "SPG", "AVB", "EQR", "MAA", "UDR", "CPT", "ESS",
        "WY", "ARE", "BXP", "KIM", "REG", "FRT", "HST",
    ],

    # ═══════════════════════════════════════════════════════
    # USA — DOW JONES 30
    # ═══════════════════════════════════════════════════════
    "DOW_JONES_30": [
        "AAPL", "AMGN", "AXP", "BA", "CAT", "CRM", "CSCO",
        "CVX", "DIS", "DOW", "GS", "HD", "HON", "IBM",
        "INTC", "JNJ", "JPM", "KO", "MCD", "MMM",
        "MRK", "MSFT", "NKE", "PG", "TRV", "UNH",
        "V", "VZ", "WBA", "WMT",
    ],

    # ═══════════════════════════════════════════════════════
    # USA — NASDAQ GROWTH & DISRUPTIVE TECH
    # ═══════════════════════════════════════════════════════
    "NASDAQ_GROWTH_TECH": [
        "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA",
        "AVGO", "NFLX", "ADBE", "AMD", "QCOM", "TXN", "INTU", "AMAT",
        "ISRG", "BKNG", "VRTX", "PANW", "MU", "SNPS", "CDNS", "KLAC",
        "MELI", "PYPL", "SNOW", "PLTR", "SMCI", "VRT", "DECK",
        "SOFI", "AFRM", "COIN", "DKNG", "RBLX", "SNAP",
        "ZM", "DOCU", "OKTA", "NET", "CFLT", "MDB",
        "HOOD", "IONQ", "RXRX", "SOUN", "BBAI",
    ],

    # ═══════════════════════════════════════════════════════
    # USA — SIN STOCKS / TABAK / ALKOHOL / SWEETS
    # ═══════════════════════════════════════════════════════
    "SIN_STOCKS_SWEETS_ENERGY": [
        "PM", "MO", "BTI", "BATS.L", "IMB.L", "2914.T", "UVV",
        "DEO", "RI.PA", "BF-B", "STZ", "BUD", "HEIA.AS", "HEIO.AS",
        "CARL-B.CO", "TAP", "CAMP.MI", "LVMH.PA",
        "MDLZ", "BN.PA", "UMG.AS", "DIS", "HSY", "NESN.SW", "LINDT.SW",
        "MNST", "CELH", "KDP", "BF-B", "CPR.MI",
    ],

    # ═══════════════════════════════════════════════════════
    # GROSSBRITANNIEN — FTSE 100
    # ═══════════════════════════════════════════════════════
    "FTSE100": [
        "AZN.L",  "HSBA.L", "ULVR.L", "GSK.L",  "RIO.L",
        "BP.L",   "SHEL.L", "BATS.L", "REL.L",  "NG.L",
        "DGE.L",  "IMB.L",  "LSEG.L", "LLOY.L", "BARC.L",
        "NWG.L",  "STAN.L", "PRU.L",  "LGEN.L", "AV.L",
        "MNG.L",  "RR.L",   "BA.L",   "MNDI.L", "SMDS.L",
        "CRH.L",  "ANTO.L", "AAL.L",  "GLEN.L", "BHP.L",
        "SVT.L",  "UU.L",   "SSE.L",  "BDEV.L", "PSN.L",
        "TW.L",   "BKG.L",  "SGRO.L", "BLND.L", "LAND.L",
        "WPP.L",  "OCDO.L", "MKS.L",  "NEXT.L", "JD.L",
        "HBR.L",  "IMI.L",  "EXPN.L", "HLMA.L", "WEIR.L",
        "TSCO.L", "SBRY.L", "KGF.L",  "AUTO.L", "III.L", "RKT.L",
    ],

    # ═══════════════════════════════════════════════════════
    # CHINA — TECH & INTERNET (US ADR + HK)
    # ═══════════════════════════════════════════════════════
    "CHINA_TECH_INTERNET": [
        "BABA",    "TCEHY",   "JD",      "BIDU",    "PDD",
        "NTES",    "BILI",    "IQ",      "VIPS",    "MOMO",
        "YMM",     "FINV",    "ZH",      "TIGR",    "FUTU",
        "LKNCY",   "TUYA",    "KC",
        "9988.HK", "0700.HK", "9618.HK", "9888.HK", "9999.HK",
        "9626.HK", "0992.HK",
    ],
    "CHINA_FINANCE_ENERGY_EV": [
        "NIO",     "XPEV",    "LI",      "BEKE",    "YUMC",
        "TAL",     "EDU",     "GOTU",    "DAO",
        "0939.HK", "1398.HK", "3988.HK", "0941.HK", "0728.HK",
        "0762.HK", "2628.HK", "0386.HK", "0857.HK", "1088.HK",
        "0175.HK", "9868.HK", "2015.HK",
    ],

    # ═══════════════════════════════════════════════════════
    # SÜDKOREA — KOSPI
    # ═══════════════════════════════════════════════════════
    "KOSPI_KOREA": [
        "005930.KS", "000660.KS", "005380.KS", "000270.KS", "005490.KS",
        "051910.KS", "006400.KS", "035420.KS", "035720.KS", "012330.KS",
        "066570.KS", "003550.KS", "028260.KS", "086790.KS", "105560.KS",
        "055550.KS", "032830.KS", "017670.KS", "030200.KS", "015760.KS",
        "096770.KS", "010950.KS", "034220.KS", "009150.KS", "011200.KS",
        "018260.KS", "032640.KS", "011070.KS", "042700.KS", "247540.KS",
        "086280.KS",
    ],
    "KOREA_ADR": [
        "KEP", "KT", "SKM", "PKX", "HMC",
    ],

    # ═══════════════════════════════════════════════════════
    # JAPAN — NIKKEI 225 AUSWAHL
    # ═══════════════════════════════════════════════════════
    "NIKKEI_SELECTION": [
        "7203.T",  # Toyota Motor
        "6758.T",  # Sony Group
        "9984.T",  # SoftBank Group
        "6861.T",  # Keyence
        "8306.T",  # Mitsubishi UFJ Financial
        "9432.T",  # NTT
        "6367.T",  # Daikin Industries
        "6501.T",  # Hitachi
        "4519.T",  # Chugai Pharmaceutical
        "9433.T",  # KDDI
        "8035.T",  # Tokyo Electron
        "6594.T",  # Nidec
        "4543.T",  # Terumo
        "7751.T",  # Canon
        "7267.T",  # Honda Motor
        "6702.T",  # Fujitsu
        "8411.T",  # Mizuho Financial
        "7741.T",  # HOYA
        "4063.T",  # Shin-Etsu Chemical
        "9983.T",  # Fast Retailing (Uniqlo)
        "2914.T",  # Japan Tobacco
        "7974.T",  # Nintendo
        "4661.T",  # Oriental Land (Disney Japan)
        "6954.T",  # Fanuc
        "6971.T",  # Kyocera
        "5108.T",  # Bridgestone
        "8801.T",  # Mitsui Fudosan
        "3382.T",  # Seven & i Holdings
        "2502.T",  # Asahi Group
        "4901.T",  # Fujifilm Holdings
    ],

    # ═══════════════════════════════════════════════════════
    # DEUTSCHLAND — DAX / MDAX / SDAX
    # ═══════════════════════════════════════════════════════
    "DAX": [
        "ADS.DE", "AIR.DE", "ALV.DE", "BAS.DE", "BAYN.DE", "BEI.DE",
        "BMW.DE", "CBK.DE", "CON.DE", "1COV.DE", "DTG.DE", "DBK.DE",
        "DB1.DE", "DHL.DE", "DTE.DE", "EOAN.DE", "ENR.DE", "FRE.DE",
        "HEI.DE", "HEN3.DE", "HNR1.DE", "IFX.DE", "MBG.DE", "MRK.DE",
        "MTX.DE", "MUV2.DE", "P911.DE", "PAH3.DE", "PUM.DE", "RHM.DE",
        "RWE.DE", "SAP.DE", "SRT3.DE", "SHL.DE", "SIE.DE", "SY1.DE",
        "TKA.DE", "VNA.DE", "VOW3.DE", "ZAL.DE",
    ],
    "MDAX": [
        "BC8.DE", "BNR.DE", "BOSS.DE", "DEQ.DE", "DUE.DE", "EVD.DE",
        "EVK.DE", "FPE.DE", "FRA.DE", "FME.DE", "GXI.DE", "HNR1.DE",
        "HHE.DE", "HOT.DE", "JUN3.DE", "KRN.DE", "LAN.DE", "LEG.DE",
        "NDX1.DE", "NEM.DE", "PUM.DE", "SAF.DE", "SDF.DE",
        "SIX2.DE", "SZG.DE", "TAG.DE", "TLX.DE", "VNA.DE",
        "WAF.DE", "WCH.DE",
    ],
    "SDAX": [
        "1U1.DE",  "B7A.DE",  "BIL.DE",  "BVB.DE",  "C3X.DE",
        "CEC.DE",  "DIC.DE",  "DWNI.DE", "FIE.DE",  "FRA.DE",
        "FNTN.DE", "GFT.DE",  "GNL.DE",  "HHFA.DE", "HLAG.DE",
        "HDD.DE",  "HORN.DE", "IVU.DE",  "JEN.DE",  "JOST.DE",
        "KLO.DE",  "KWS.DE",  "MLP.DE",  "O2D.DE",  "PBB.DE",
        "PNE3.DE", "PSM.DE",  "QIA.DE",  "SAF.DE",  "SDF.DE",
        "STR.DE",  "TAG.DE",  "TTK.DE",  "VAR1.DE", "VIP.DE",
        "WUW.DE", "TUI1.DE", "LXS.DE",
    ],

    # ═══════════════════════════════════════════════════════
    # FRANKREICH — CAC 40
    # ═══════════════════════════════════════════════════════
    "CAC40": [
        "AI.PA",    "AIR.PA",   "ALO.PA",   "CS.PA",    "BN.PA",
        "DSY.PA",   "ENGI.PA",  "EL.PA",    "RMS.PA",   "KER.PA",
        "OR.PA",    "LR.PA",    "MC.PA",    "ML.PA",    "ORA.PA",
        "RI.PA",    "PUB.PA",   "RNO.PA",   "SAF.PA",   "SGO.PA",
        "SAN.PA",   "SU.PA",    "GLE.PA",   "STLA.PA",  "STMPA.PA",
        "HO.PA",    "TTE.PA",   "CA.PA",    "BNP.PA",   "ACA.PA",
        "VIE.PA",   "DG.PA",    "WLN.PA",   "EN.PA",    "FR.PA",
        "LI.PA",    "URW.PA",   "MT.AS",
    ],

    # ═══════════════════════════════════════════════════════
    # SPANIEN — IBEX 35
    # ═══════════════════════════════════════════════════════
    "IBEX35": [
        "ACS.MC",  "ACX.MC",  "AMS.MC",  "ANA.MC",  "BBVA.MC",
        "BKT.MC",  "CABK.MC", "CLNX.MC", "COL.MC",  "ELE.MC",
        "ENG.MC",  "FER.MC",  "GRF.MC",  "IAG.MC",  "IBE.MC",
        "IDR.MC",  "ITX.MC",  "MAP.MC",  "MEL.MC",  "MRL.MC",
        "NTGY.MC", "RED.MC",  "REP.MC",  "SAB.MC",  "SAN.MC",
        "TEF.MC",  "VIS.MC",
    ],

    # ═══════════════════════════════════════════════════════
    # ITALIEN — FTSE MIB
    # ═══════════════════════════════════════════════════════
    "FTSE_MIB": [
        "A2A.MI",   "AMP.MI",   "BAMI.MI",  "BZU.MI",  "CNHI.MI",
        "ENEL.MI",  "ENI.MI",   "FCMA.MI",  "G.MI",    "HER.MI",
        "IG.MI",    "INW.MI",   "ISP.MI",   "LDO.MI",  "MB.MI",
        "MONC.MI",  "PIRC.MI",  "PRY.MI",   "RACE.MI", "REC.MI",
        "SRG.MI",   "STM.MI",   "TEN.MI",   "TIT.MI",  "TRN.MI",
        "UCG.MI",   "UNI.MI",
    ],

    # ═══════════════════════════════════════════════════════
    # NIEDERLANDE — AEX
    # ═══════════════════════════════════════════════════════
    "AEX_NETHERLANDS": [
        "ADYEN.AS", "AD.AS",   "AGN.AS",  "AKZA.AS", "MT.AS",
        "ASML.AS",  "HEIA.AS", "HEIO.AS", "IMCD.AS", "INGA.AS",
        "PHIA.AS",  "PRX.AS",  "RAND.AS", "REN.AS",  "SHELL.AS",
        "NN.AS",    "WKL.AS",  "UMG.AS",  "BESI.AS", "LIGHT.AS",
    ],

    # ═══════════════════════════════════════════════════════
    # SCHWEIZ — SMI
    # ═══════════════════════════════════════════════════════
    "SMI_SWITZERLAND": [
        "NESN.SW",  "ROG.SW",   "NOVN.SW",  "ABBN.SW",  "ADEN.SW",
        "ALC.SW",   "CFR.SW",   "CSGN.SW",  "GEBN.SW",  "GIVN.SW",
        "HOLN.SW",  "KNIN.SW",  "LONN.SW",  "PGHN.SW",  "SGSN.SW",
        "SIKA.SW",  "SLHN.SW",  "SRENH.SW", "UBSG.SW",  "ZURN.SW",
        "LINDT.SW", "BALN.SW",
    ],

    # ═══════════════════════════════════════════════════════
    # SKANDINAVIEN — OMX Nordic
    # ═══════════════════════════════════════════════════════
    "NORDIC_OMXS": [
        "VOLV-B.ST", "ERIC-B.ST", "ASSA-B.ST", "SEB-A.ST",  "SHB-A.ST",
        "SWED-A.ST", "ATCO-A.ST", "SAND.ST",   "SKF-B.ST",  "ALFA.ST",
        "INVE-B.ST", "ESSITY-B.ST","NDA-SE.ST", "LOOMIS.ST", "HEXA-B.ST",
        "NIBE-B.ST", "HUFV-A.ST", "HUSQ-B.ST", "KINV-B.ST", "SINCH.ST",
        # Dänemark
        "NOVO-B.CO", "CARL-B.CO", "MAERSK-B.CO","ORSTED.CO","DEMANT.CO",
        "COLOB.CO",  "GN.CO",     "ROCK-B.CO",
        # Norwegen
        "EQNR",      "AKRBP.OL",  "VAR.OL",    "DNO.OL",   "MOWI.OL",
        "TEL.OL",    "ORK.OL",    "SALM.OL",   "YAR.OL",
        # Finnland
        "KNEBV.HE",  "NESTE.HE",  "FORTUM.HE", "WRT1V.HE", "OUT1V.HE",
    ],

    # ═══════════════════════════════════════════════════════
    # EURO STOXX 50
    # ═══════════════════════════════════════════════════════
    "EURO_STOXX_50": [
        "AD.AS",   "AI.PA",   "AIR.PA",  "ALV.DE",  "ASML.AS",
        "CS.PA",   "BAS.DE",  "BAYN.DE", "BBVA.MC", "SAN.MC",
        "BMW.DE",  "BNP.PA",  "BN.PA",   "DHL.DE",  "DTE.DE",
        "ENEL.MI", "ENI.MI",  "EL.PA",   "STLA.PA", "IBE.MC",
        "ITX.MC",  "IFX.DE",  "INGA.AS", "ISP.MI",  "KER.PA",
        "KNEBV.HE","OR.PA",   "MC.PA",   "MBG.DE",  "MUV2.DE",
        "RI.PA",   "PRX.AS",  "SAF.PA",  "SGO.PA",  "SAN.PA",
        "SAP.DE",  "SU.PA",   "SIE.DE",  "TTE.PA",  "DG.PA",
        "VOW3.DE", "VNA.DE",  "WKL.AS",  "HER.PA",  "RACE.MI",
        "UCG.MI",  "ENGI.PA", "VIE.PA",  "ADS.DE",
    ],

    # ═══════════════════════════════════════════════════════
    # ENERGIE & ÖL / GAS (Global)
    # ═══════════════════════════════════════════════════════
    "ENERGY_OIL_GAS": [
        "XOM",     "CVX",     "COP",     "EOG",     "SLB",
        "HAL",     "MPC",     "PSX",     "VLO",     "DVN",
        "FANG",    "APA",     "CTRA",    "OXY",     "PBR",
        "MRO",     "HES",     "BKR",     "CHRD",    "MTDR",
        "SM",      "PR",      "SHEL.L",  "BP.L",    "TTE.PA",
        "EQNR",    "AKRBP.OL","VAR.OL",  "DNO.OL",  "OMV.VI",
        "HBR.L",   "ENI.MI",  "REP.MC",  "0386.HK", "0857.HK",
        "NESTE.HE","YAR.OL",
    ],

    # ═══════════════════════════════════════════════════════
    # MINING & ROHSTOFFE (Global)
    # ═══════════════════════════════════════════════════════
    "MINING_CYCLICALS": [
        "RIO",    "RIO.L",  "BHP",    "VALE",   "GLNCY",
        "GLEN.L", "AAL.L",  "FCX",    "NEM",    "GOLD",
        "AEM",    "GFI",    "ALB",    "SQM",    "CCJ",
        "CAT",    "DE",     "MMM",    "GE",     "HON",
        "LMT",    "BA",     "UPS",    "FDX",    "NSC",
        "UNP",    "EMR",    "ETN",    "ITW",    "DOW",
        "LYB",    "CTVA",   "NUE",    "STLD",   "AA",
        "CF",     "MOS",    "F",      "GM",     "STLA",
        "ANTO.L", "1088.HK","005490.KS",
    ],

    # ═══════════════════════════════════════════════════════
    # IMMOBILIEN — Europa (Bau & REIT)
    # ═══════════════════════════════════════════════════════
    "REAL_ESTATE_CONSTRUCTION_EUROPE": [
        "VNA.DE",  "LEG.DE",  "HOT.DE",  "TAG.DE",  "DWNI.DE",
        "DG.PA",   "SGO.PA",  "EN.PA",   "LI.PA",   "URW.PA",
        "BDEV.L",  "PSN.L",   "TW.L",    "BLND.L",  "SGRO.L",
        "LAND.L",  "BKG.L",   "ACS.MC",  "FER.MC",  "SKAB.ST",
        "SBB-B.ST","COL.MC",  "MRL.MC",
    ],

    # ═══════════════════════════════════════════════════════
    # VERSORGER — Europa & USA
    # ═══════════════════════════════════════════════════════
    "UTILITIES_INFRASTRUCTURE": [
        "VIE.PA",  "ENGI.PA", "IBE.MC",  "ENEL.MI", "EDP.LS",
        "ENG.MC",  "REE.MC",  "TER.MI",  "NG.L",    "UU.L",
        "RWE.DE",  "EOAN.DE", "NEE",     "DUK",     "SO",
        "D",       "AEP",     "SRE",     "AWK",     "SSE.L",
        "SVT.L",   "A2A.MI",  "SRG.MI",  "IG.MI",   "FORTUM.HE",
        "ORSTED.CO","NESTE.HE",
    ],

    # ═══════════════════════════════════════════════════════
    # EMERGING MARKETS — Breite Auswahl
    # ═══════════════════════════════════════════════════════
    "EMERGING_MARKETS": [
        # Brasilien
        "PBR",    "VALE",   "ITUB",   "BBD",    "ABEV",
        "BRFS",   "EMBR3.SA","PETR4.SA",
        # Indien (US ADR / Listing)
        "INFY",   "WIT",    "HDB",    "IBN",    "TTM",
        "SIFY",   "VEDL",
        # Südafrika
        "NPN.JO", "AGL.JO", "FSR.JO", "SBK.JO",
        # Türkei
        "TKFEN.IS","BIMAS.IS","EREGL.IS",
        # Mexiko
        "AMXL.MX","FEMSAUBD.MX",
        # Indonesien / Philippinen / Thailand (US ADR)
        "TLKM",   "BSRR",
        # Saudi Arabien / GCC
        "2222.SR", # Saudi Aramco
        # Israel
        "CHKP",   "NICE",   "CHL",    "ESLT",
    ],

    # ═══════════════════════════════════════════════════════
    # HEALTHCARE & PHARMA (Global)
    # ═══════════════════════════════════════════════════════
    "HEALTHCARE_PHARMA": [
        "JNJ",    "PFE",    "ABBV",   "LLY",    "MRK",
        "NVO",    "AZN",    "GSK",    "SYK",    "UNH",
        "NOVN.SW","ROG.SW", "SAN.PA", "BAY.DE", "BAYN.DE",
        "AZN.L",  "GSK.L",  "4519.T", "4543.T", "REC.MI",
        "GRF.MC",
    ],

    # ═══════════════════════════════════════════════════════
    # FINANCIALS & PAYMENTS (Global)
    # ═══════════════════════════════════════════════════════
    "FINANCIALS_PAYMENTS": [
        "JPM",    "BAC",    "V",      "MA",     "AXP",
        "BLK",    "MS",     "GS",     "HSBC",   "HSBA.L",
        "STAN.L", "LLOY.L", "BARC.L", "BNP.PA", "SAN.MC",
        "BBVA.MC","UCG.MI", "ISP.MI", "DBK.DE", "CBK.DE",
        "ADYEN.AS","8306.T","8411.T", "105560.KS","055550.KS",
        "0939.HK","1398.HK",
    ],

    # ═══════════════════════════════════════════════════════
    # CONSUMER STAPLES (Global)
    # ═══════════════════════════════════════════════════════
    "CONSUMER_STAPLES": [
        "PG",     "KO",     "PEP",    "WMT",    "COST",
        "NSRGY",  "UL",     "CL",     "KHC",    "ULVR.L",
        "NESN.SW","BN.PA",  "DGE.L",  "HEIA.AS","CARL-B.CO",
        "NOVO-B.CO","3382.T","2502.T","TSCO.L", "MKS.L",
    ],

    # ═══════════════════════════════════════════════════════
    # REITS — USA & Global
    # ═══════════════════════════════════════════════════════
    "REITS_REAL_ESTATE": [
        "O",   "AMT",  "PLD",  "CCI",  "SPG",
        "VICI","DLR",  "PSA",  "EQIX", "AVB",
        "EQR", "MAA",  "ARE",  "BXP",  "WY",
    ],

    # ═══════════════════════════════════════════════════════
    # CRYPTO & FINTECH (Börsengelistet)
    # ═══════════════════════════════════════════════════════
    "CRYPTO_FINTECH": [
        "COIN",   "MSTR",   "RIOT",   "MARA",   "CLSK",
        "HUT",    "BITF",   "CIFR",   "WULF",   "IREN",
        "HOOD",   "SOFI",   "AFRM",   "UPST",   "LC",
        "SQ",     "PYPL",   "ADYEN.AS",
    ],

    # ═══════════════════════════════════════════════════════
    # EV & CLEAN ENERGY (Global)
    # ═══════════════════════════════════════════════════════
    "EV_CLEAN_ENERGY": [
        "TSLA",   "RIVN",   "LCID",   "NIO",    "XPEV",
        "LI",     "NKLA",   "FSR",    "BLNK",   "CHPT",
        "EVGO",   "FCEL",   "PLUG",   "BE",     "ENPH",
        "SEDG",   "ARRY",   "NEE",    "ORSTED.CO","IBE.MC",
        "EOAN.DE","RWE.DE", "NIBE-B.ST","0175.HK","9868.HK",
        "2015.HK","066570.KS","051910.KS","006400.KS",
    ],

    # ═══════════════════════════════════════════════════════
    # DEFENSE & RÜSTUNG (Global)
    # ═══════════════════════════════════════════════════════
    "DEFENSE_AEROSPACE": [
        "LMT",    "RTX",    "NOC",    "GD",     "BA",
        "HII",    "L3T",    "TDG",    "HEI",    "HEICO",
        "RHM.DE", "MTX.DE", "AIR.DE", "SAF.PA", "HO.PA",
        "BA.L",   "RR.L",   "LDO.MI", "ESLT",
    ],

    # ═══════════════════════════════════════════════════════
    # LUXURY & FASHION (Global)
    # ═══════════════════════════════════════════════════════
    "LUXURY_FASHION": [
        "MC.PA",  "RMS.PA", "KER.PA", "RACE.MI","MONC.MI",
        "OR.PA",  "EL.PA",  "LVMH.PA","CFR.SW",  "LINDT.SW",
        "ADS.DE", "PUM.DE", "NKE",    "RL",      "TPR",
        "CPRI",   "TIF",    "EL",
    ],
}

# ═══════════════════════════════════════════════════════════════
# WÄHRUNGS-MAPPING nach Ticker-Suffix
# ═══════════════════════════════════════════════════════════════
CURRENCY_MAP = {
    # Euro-Raum
    ".DE": "€",  ".PA": "€",  ".MC": "€",  ".MI": "€",
    ".AS": "€",  ".VI": "€",  ".LS": "€",  ".HE": "€",
    # Britisches Pfund
    ".L":  "£",
    # Schweizer Franken
    ".SW": "CHF",
    # Skandinavien
    ".OL": "NOK", ".ST": "SEK", ".CO": "DKK",
    # Asien
    ".T":  "¥",   ".HK": "HK$", ".KS": "₩",
    # Sonstige
    ".JO": "ZAR", ".SA": "BRL", ".MX": "MXN",
    ".IS": "TRY", ".SR": "SAR",
}


def get_currency(ticker: str) -> str:
    """Gibt das Währungssymbol für einen Ticker zurück."""
    upper = ticker.upper()
    for suffix, symbol in CURRENCY_MAP.items():
        if upper.endswith(suffix.upper()):
            return symbol
    return "$"  # Default: US-Dollar


def get_all_tickers() -> list:
    """Gibt alle einzigartigen Ticker in fester (deterministischer) Reihenfolge zurück."""
    seen   = set()
    result = []
    for tickers in TICKER_LISTS.values():
        for t in tickers:
            if t not in seen:
                seen.add(t)
                result.append(t)
    return sorted(result)


def get_tickers_by_group(group: str) -> list:
    """Gibt die Ticker einer bestimmten Gruppe zurück."""
    return TICKER_LISTS.get(group, [])


def get_all_groups() -> list:
    """Gibt alle Gruppen-Namen zurück."""
    return list(TICKER_LISTS.keys())


def get_ticker_count() -> int:
    """Gibt die Anzahl einzigartiger Ticker zurück."""
    return len(get_all_tickers())
