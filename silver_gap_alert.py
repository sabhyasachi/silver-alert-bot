import os
import re
import requests
import yfinance as yf
from datetime import datetime

# ---------------- CONFIG ----------------
TICKER_A = "GROWWSLVR.NS"
TICKER_B = "SILVERIETF.NS"

THRESHOLD_ETF = .01        # condition-1: abs(A-B) > 5
MAX_DIFF_TO_MCX = 50.0     # condition-2: abs(A - MCX_per_gram) < 30

GROWW_MCX_URL = "https://groww.in/commodities/futures/mcx_silvermic"
# Benchmark inputs (machine-readable, no JS scraping)
SILVER_FUTURES = "SI=F"   # Silver futures (USD per troy ounce)
USDINR = "USDINR=X"       # USD/INR FX rate

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

# ---------------- HELPERS ----------------
def send_telegram(text: str):
    if not BOT_TOKEN or not CHAT_ID or "PUT_YOUR" in BOT_TOKEN or "PUT_YOUR" in CHAT_ID:
        raise RuntimeError("BOT_TOKEN/CHAT_ID missing. Set them as environment variables or GitHub Secrets.")

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    r = requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=20)
    r.raise_for_status()


def last_price_yf(ticker: str) -> float:
    t = yf.Ticker(ticker)

    price = None
    try:
        price = t.fast_info.get("last_price")
    except Exception:
        pass

    if not price:
        hist = t.history(period="1d", interval="1m")
        if hist.empty:
            raise RuntimeError(f"No data for {ticker}")
        price = float(hist["Close"].iloc[-1])

    return float(price)


def mcx_silvermic_price_inr_per_kg_from_groww(url: str) -> float:
    """
    Scrapes Groww public HTML futures page.
    Example snippet includes: "₹2,46,100.00"
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
    }
    html = requests.get(url, headers=headers, timeout=25).text

    # Prefer extracting the first main price shown near the header
    # On Groww page, the main price appears like: "₹2,46,100.00"
    m = re.search(r"Silver Micro.*?₹\s*([\d,]+(?:\.\d+)?)", html, flags=re.DOTALL | re.IGNORECASE)
    if not m:
        # fallback: first ₹ amount in page
        m = re.search(r"₹\s*([\d,]+(?:\.\d+)?)", html)
    if not m:
        raise RuntimeError("Could not parse MCX SILVERMIC price from Groww page (markup changed or blocked).")

    price = float(m.group(1).replace(",", ""))


    return price


# ---------------- MAIN ----------------
def main():
    a = last_price_yf(TICKER_A)
    b = last_price_yf(TICKER_B)
    diff_etf = a - b

    mcx_per_kg = mcx_silvermic_price_inr_per_kg_from_groww(GROWW_MCX_URL)
    mcx_per_gram = mcx_per_kg / 1000.0
    diff_to_mcx = a - mcx_per_gram

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(
        "A(GROWWSLVR):", a,
        "B(SILVERIETF):", b,
        "ETF diff:", diff_etf,
        "MCX/kg:", mcx_per_kg,
        "MCX/g:", mcx_per_gram,
        "A-MCX diff:", diff_to_mcx
    )

    # Your final condition:
    if abs(diff_etf) > THRESHOLD_ETF and abs(diff_to_mcx) < MAX_DIFF_TO_MCX:
        msg = (
            "🚨 Silver Alert\n\n"
            f"GROWWSLVR: {a:.2f}\n"
            f"SILVERIETF: {b:.2f}\n"
            f"ETF Gap (A-B): {diff_etf:.2f} (>|{THRESHOLD_ETF}|)\n\n"
            f"MCX SILVERMIC (₹/kg): {mcx_per_kg:.0f}\n"
            f"MCX (₹/g): {mcx_per_gram:.2f}\n"
            f"A - MCX Gap: {diff_to_mcx:.2f} (<|{MAX_DIFF_TO_MCX}|)\n\n"
            f"⏱ {now}"
        )
        send_telegram(msg)
    else:
        print("No alert (conditions not met).")


if __name__ == "__main__":
    main()
