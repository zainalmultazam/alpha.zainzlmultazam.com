"""
Universe Saham Amerika Serikat (US Stocks: NYSE & NASDAQ).
Berisi saham-saham likuid berkapitalisasi besar dan berkarakter momentum/growth
(Mega-Cap Tech, AI Hardware/Software, Semikonduktor, Biomedis, Energi, & Sektoral ETFs).
"""

from typing import List, Dict

UNIVERSE_US: List[Dict[str, str]] = [
    # ── Mega-Cap Tech & AI Leaders ───────────────────────────────────────
    {"ticker": "NVDA", "name": "NVIDIA Corporation", "sector": "Semiconductors", "exchange": "NASDAQ"},
    {"ticker": "AAPL", "name": "Apple Inc.", "sector": "Consumer Electronics", "exchange": "NASDAQ"},
    {"ticker": "MSFT", "name": "Microsoft Corporation", "sector": "Software - Infrastructure", "exchange": "NASDAQ"},
    {"ticker": "AMZN", "name": "Amazon.com, Inc.", "sector": "Internet Retail", "exchange": "NASDAQ"},
    {"ticker": "GOOGL", "name": "Alphabet Inc.", "sector": "Internet Content & Information", "exchange": "NASDAQ"},
    {"ticker": "META", "name": "Meta Platforms, Inc.", "sector": "Internet Content & Information", "exchange": "NASDAQ"},
    {"ticker": "TSLA", "name": "Tesla, Inc.", "sector": "Auto Manufacturers", "exchange": "NASDAQ"},
    {"ticker": "PLTR", "name": "Palantir Technologies Inc.", "sector": "Software - Infrastructure", "exchange": "NYSE"},
    {"ticker": "AMD", "name": "Advanced Micro Devices, Inc.", "sector": "Semiconductors", "exchange": "NASDAQ"},
    {"ticker": "AVGO", "name": "Broadcom Inc.", "sector": "Semiconductors", "exchange": "NASDAQ"},
    {"ticker": "NFLX", "name": "Netflix, Inc.", "sector": "Entertainment", "exchange": "NASDAQ"},
    
    # ── High Beta Growth & Cloud/AI Software ──────────────────────────────
    {"ticker": "CRM", "name": "Salesforce, Inc.", "sector": "Software - Application", "exchange": "NYSE"},
    {"ticker": "ORCL", "name": "Oracle Corporation", "sector": "Software - Infrastructure", "exchange": "NYSE"},
    {"ticker": "ADBE", "name": "Adobe Inc.", "sector": "Software - Infrastructure", "exchange": "NASDAQ"},
    {"ticker": "NOW", "name": "ServiceNow, Inc.", "sector": "Software - Application", "exchange": "NYSE"},
    {"ticker": "SNOW", "name": "Snowflake Inc.", "sector": "Software - Application", "exchange": "NYSE"},
    {"ticker": "CRWD", "name": "CrowdStrike Holdings, Inc.", "sector": "Cybersecurity", "exchange": "NASDAQ"},
    {"ticker": "PANW", "name": "Palo Alto Networks, Inc.", "sector": "Cybersecurity", "exchange": "NASDAQ"},
    {"ticker": "NET", "name": "Cloudflare, Inc.", "sector": "Software - Infrastructure", "exchange": "NYSE"},
    {"ticker": "DDOG", "name": "Datadog, Inc.", "sector": "Software - Application", "exchange": "NASDAQ"},
    {"ticker": "MDB", "name": "MongoDB, Inc.", "sector": "Software - Infrastructure", "exchange": "NASDAQ"},
    {"ticker": "APP", "name": "AppLovin Corporation", "sector": "Software - Application", "exchange": "NASDAQ"},
    {"ticker": "UBER", "name": "Uber Technologies, Inc.", "sector": "Software - Application", "exchange": "NYSE"},
    {"ticker": "ABNB", "name": "Airbnb, Inc.", "sector": "Travel Services", "exchange": "NASDAQ"},
    {"ticker": "DASH", "name": "DoorDash, Inc.", "sector": "Internet Retail", "exchange": "NASDAQ"},

    # ── Semiconductors & Hardware Equipment ───────────────────────────────
    {"ticker": "TSM", "name": "Taiwan Semiconductor Manufacturing", "sector": "Semiconductors", "exchange": "NYSE"},
    {"ticker": "QCOM", "name": "QUALCOMM Incorporated", "sector": "Semiconductors", "exchange": "NASDAQ"},
    {"ticker": "TXN", "name": "Texas Instruments Incorporated", "sector": "Semiconductors", "exchange": "NASDAQ"},
    {"ticker": "MU", "name": "Micron Technology, Inc.", "sector": "Semiconductors", "exchange": "NASDAQ"},
    {"ticker": "INTC", "name": "Intel Corporation", "sector": "Semiconductors", "exchange": "NASDAQ"},
    {"ticker": "AMAT", "name": "Applied Materials, Inc.", "sector": "Semiconductor Equipment", "exchange": "NASDAQ"},
    {"ticker": "LRCX", "name": "Lam Research Corporation", "sector": "Semiconductor Equipment", "exchange": "NASDAQ"},
    {"ticker": "KLAC", "name": "KLA Corporation", "sector": "Semiconductor Equipment", "exchange": "NASDAQ"},
    {"ticker": "ARM", "name": "Arm Holdings plc", "sector": "Semiconductors", "exchange": "NASDAQ"},
    {"ticker": "ASML", "name": "ASML Holding N.V.", "sector": "Semiconductor Equipment", "exchange": "NASDAQ"},
    {"ticker": "MRVL", "name": "Marvell Technology, Inc.", "sector": "Semiconductors", "exchange": "NASDAQ"},
    {"ticker": "SMCI", "name": "Super Micro Computer, Inc.", "sector": "Computer Hardware", "exchange": "NASDAQ"},
    {"ticker": "DELL", "name": "Dell Technologies Inc.", "sector": "Computer Hardware", "exchange": "NYSE"},

    # ── Fintech, Crypto Proxies & Brokers ────────────────────────────────
    {"ticker": "V", "name": "Visa Inc.", "sector": "Credit Services", "exchange": "NYSE"},
    {"ticker": "MA", "name": "Mastercard Incorporated", "sector": "Credit Services", "exchange": "NYSE"},
    {"ticker": "PYPL", "name": "PayPal Holdings, Inc.", "sector": "Credit Services", "exchange": "NASDAQ"},
    {"ticker": "COIN", "name": "Coinbase Global, Inc.", "sector": "Financial Services", "exchange": "NASDAQ"},
    {"ticker": "MSTR", "name": "MicroStrategy Incorporated", "sector": "Software - Application", "exchange": "NASDAQ"},
    {"ticker": "HOOD", "name": "Robinhood Markets, Inc.", "sector": "Capital Markets", "exchange": "NASDAQ"},
    {"ticker": "AFRM", "name": "Affirm Holdings, Inc.", "sector": "Credit Services", "exchange": "NASDAQ"},
    {"ticker": "SOFI", "name": "SoFi Technologies, Inc.", "sector": "Credit Services", "exchange": "NASDAQ"},

    # ── Financials & Wall Street Banks ───────────────────────────────────
    {"ticker": "JPM", "name": "JPMorgan Chase & Co.", "sector": "Banks - Diversified", "exchange": "NYSE"},
    {"ticker": "BAC", "name": "Bank of America Corporation", "sector": "Banks - Diversified", "exchange": "NYSE"},
    {"ticker": "GS", "name": "The Goldman Sachs Group, Inc.", "sector": "Capital Markets", "exchange": "NYSE"},
    {"ticker": "MS", "name": "Morgan Stanley", "sector": "Capital Markets", "exchange": "NYSE"},
    {"ticker": "WFC", "name": "Wells Fargo & Company", "sector": "Banks - Diversified", "exchange": "NYSE"},
    {"ticker": "BLK", "name": "BlackRock, Inc.", "sector": "Asset Management", "exchange": "NYSE"},

    # ── Healthcare & BioPharma Leaders ───────────────────────────────────
    {"ticker": "LLY", "name": "Eli Lilly and Company", "sector": "Drug Manufacturers - General", "exchange": "NYSE"},
    {"ticker": "NVO", "name": "Novo Nordisk A/S", "sector": "Biotechnology", "exchange": "NYSE"},
    {"ticker": "UNH", "name": "UnitedHealth Group Incorporated", "sector": "Healthcare Plans", "exchange": "NYSE"},
    {"ticker": "JNJ", "name": "Johnson & Johnson", "sector": "Drug Manufacturers - General", "exchange": "NYSE"},
    {"ticker": "ABBV", "name": "AbbVie Inc.", "sector": "Drug Manufacturers - General", "exchange": "NYSE"},
    {"ticker": "MRK", "name": "Merck & Co., Inc.", "sector": "Drug Manufacturers - General", "exchange": "NYSE"},
    {"ticker": "ISRG", "name": "Intuitive Surgical, Inc.", "sector": "Medical Instruments & Supplies", "exchange": "NASDAQ"},
    {"ticker": "VRTX", "name": "Vertex Pharmaceuticals Incorporated", "sector": "Biotechnology", "exchange": "NASDAQ"},

    # ── Consumer, Retail & High Momentum Growth ──────────────────────────
    {"ticker": "WMT", "name": "Walmart Inc.", "sector": "Discount Stores", "exchange": "NYSE"},
    {"ticker": "COST", "name": "Costco Wholesale Corporation", "sector": "Discount Stores", "exchange": "NASDAQ"},
    {"ticker": "HD", "name": "The Home Depot, Inc.", "sector": "Home Improvement Retail", "exchange": "NYSE"},
    {"ticker": "NKE", "name": "NIKE, Inc.", "sector": "Footwear & Accessories", "exchange": "NYSE"},
    {"ticker": "SBUX", "name": "Starbucks Corporation", "sector": "Restaurants", "exchange": "NASDAQ"},
    {"ticker": "MCD", "name": "McDonald's Corporation", "sector": "Restaurants", "exchange": "NYSE"},
    {"ticker": "CMG", "name": "Chipotle Mexican Grill, Inc.", "sector": "Restaurants", "exchange": "NYSE"},
    {"ticker": "CELH", "name": "Celsius Holdings, Inc.", "sector": "Beverages - Non-Alcoholic", "exchange": "NASDAQ"},
    {"ticker": "MNST", "name": "Monster Beverage Corporation", "sector": "Beverages - Non-Alcoholic", "exchange": "NASDAQ"},
    {"ticker": "LULU", "name": "Lululemon Athletica Inc.", "sector": "Apparel Retail", "exchange": "NASDAQ"},
    {"ticker": "DECK", "name": "Deckers Outdoor Corporation", "sector": "Footwear & Accessories", "exchange": "NYSE"},
    {"ticker": "ONON", "name": "On Holding AG", "sector": "Footwear & Accessories", "exchange": "NYSE"},

    # ── Industrial, Aerospace, Defense & Energy ───────────────────────────
    {"ticker": "CAT", "name": "Caterpillar Inc.", "sector": "Farm & Heavy Construction Machinery", "exchange": "NYSE"},
    {"ticker": "GE", "name": "GE Aerospace", "sector": "Aerospace & Defense", "exchange": "NYSE"},
    {"ticker": "BA", "name": "The Boeing Company", "sector": "Aerospace & Defense", "exchange": "NYSE"},
    {"ticker": "LMT", "name": "Lockheed Martin Corporation", "sector": "Aerospace & Defense", "exchange": "NYSE"},
    {"ticker": "RTX", "name": "RTX Corporation", "sector": "Aerospace & Defense", "exchange": "NYSE"},
    {"ticker": "XOM", "name": "Exxon Mobil Corporation", "sector": "Oil & Gas Integrated", "exchange": "NYSE"},
    {"ticker": "CVX", "name": "Chevron Corporation", "sector": "Oil & Gas Integrated", "exchange": "NYSE"},
    {"ticker": "SLB", "name": "Schlumberger Limited", "sector": "Oil & Gas Equipment & Services", "exchange": "NYSE"},

    # ── Major Index & Sector ETFs (For Macro & Swing ETF Trades) ──────────
    {"ticker": "QQQ", "name": "Invesco QQQ Trust (Nasdaq 100 ETF)", "sector": "Index ETF", "exchange": "NASDAQ"},
    {"ticker": "SPY", "name": "SPDR S&P 500 ETF Trust", "sector": "Index ETF", "exchange": "NYSE"},
    {"ticker": "IWM", "name": "iShares Russell 2000 ETF (Small Cap)", "sector": "Index ETF", "exchange": "NYSE"},
    {"ticker": "SMH", "name": "VanEck Semiconductor ETF", "sector": "Sector ETF", "exchange": "NASDAQ"},
    {"ticker": "XLK", "name": "Technology Select Sector SPDR Fund", "sector": "Sector ETF", "exchange": "NYSE"},
    {"ticker": "XLF", "name": "Financial Select Sector SPDR Fund", "sector": "Sector ETF", "exchange": "NYSE"},
    {"ticker": "XLE", "name": "Energy Select Sector SPDR Fund", "sector": "Sector ETF", "exchange": "NYSE"},
    {"ticker": "GLD", "name": "SPDR Gold Shares ETF", "sector": "Commodity ETF", "exchange": "NYSE"}
]

def get_universe_us() -> List[Dict[str, str]]:
    """Mengembalikan daftar saham likuid bursa Amerika Serikat."""
    return UNIVERSE_US
