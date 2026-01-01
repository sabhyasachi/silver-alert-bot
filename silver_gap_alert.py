```python
import os
import re
import requests
import yfinance as yf
from datetime import datetime

# ---- CONFIG ----
TICKER_A = "GROWWSLVR.NS"
TICKER_B = "SILVERIETF.NS"

THRESHOLD = 5.0          # ₹ (ETF vs ETF) absolute threshold
MCX_THRESHOLD = 10.0     # ₹ (per gram) absolute threshold for (MCX/1000) vs GROWWSLVR

# MCX Silver Micro (27-Feb-2026) quote page (₹ per KGS)
MCX_SILVERMIC_URL = "https://www.indiainfoline.com/commodity/mcxfut/silvermic/27-feb-2026"

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]


def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    r = requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=20)
    r.raise_for_status()


def last_price(ticker: str) -> float:
    t = yf.Ticker(ticker)

    price = None
    try:
        price = t.fast_info.get("last_price")
    except Exception:
        pass

    if price is None:
        hist = t.history(period="1d", interval="1m")
        if hist.empty:
            raise RuntimeError(f"No data for {ticker}")
        price = float(hist["Close"].iloc[-1])

    return float(price)


def mcx_silvermic_feb27_price_kg() -> float:
    """
    Fetch MCX SILVERMIC 27-Feb-2026 last traded price from IndiaInfoline page.
    Returns price in ₹ per kg.
    """
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    r = requests.get(MCX_SILVERMIC_URL, headers=headers, timeout=20)
    r.raise_for_status()
    html = r.text

    # The page contains a line like: "Last Traded Price 2,36,058"
    m = re.search(r"Last\s+Traded\s+Price\s*([0-9,]+(?:\.[0-9]+)?)", html, re.IGNORECASE)
    if not m:
        raise RuntimeError("Could not parse MCX Silver Micro LTP from IndiaInfoline page")

    val = m.group(1).replace(",", "")
    return float(val)


def main():
    groww = last_price(TICKER_A)
    silver_etf = last_price(TICKER_B)
    etf_diff = groww - silver_etf

    mcx_kg = mcx_silvermic_feb27_price_kg()
    mcx_per_gm = mcx_kg / 1000.0
    mcx_diff = groww - mcx_per_gm

    print(
        "GROWWSLVR:", groww,
        "SILVERIETF:", silver_etf,
        "ETF diff:", etf_diff,
        "MCX SILVERMIC (₹/kg):", mcx_kg,
        "MCX/1000 (₹/gm):", mcx_per_gm,
        "GROWW - (MCX/1000):", mcx_diff,
        "ETF threshold:", THRESHOLD,
        "MCX threshold:", MCX_THRESHOLD,
    )

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ✅ Alert only if:
    # 1) ETF-vs-ETF gap is big enough, AND
    # 2) GROWW is within ₹10 of (MCX Silver Micro Feb27 / 1000)
    if abs(etf_diff) > THRESHOLD and abs(mcx_diff) < MCX_THRESHOLD:
        direction = (
            "GROWWSLVR higher than SILVERIETF"
            if etf_diff > 0
            else "SILVERIETF higher than GROWWSLVR"
        )

        msg = (
            "🚨 Silver ETF Arbitrage Alert (MCX-validated)\n\n"
            f"GROWWSLVR: {groww:.2f}\n"
            f"SILVERIETF: {silver_etf:.2f}\n"
            f"ETF Difference: {etf_diff:.2f}\n"
            f"Direction: {direction}\n\n"
            f"MCX SILVERMIC (27-Feb) ₹/kg: {mcx_kg:.2f}\n"
            f"MCX/1000 (₹/gm): {mcx_per_gm:.2f}\n"
            f"GROWW - (MCX/1000): {mcx_diff:.2f}\n"
            f"MCX Check: |diff| < {MCX_THRESHOLD:.2f}\n\n"
            f"⏱ {now}"
        )

        send_telegram(msg)


if __name__ == "__main__":
    main()
```
