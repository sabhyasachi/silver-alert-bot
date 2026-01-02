
import os
import requests
import yfinance as yf
from datetime import datetime

# ---------------- CONFIG ----------------
TICKER_A = "GROWWSLVR.NS"
TICKER_B = "SILVERIETF.NS"

THRESHOLD = 0.01          # ₹ absolute threshold for ETF-vs-ETF difference
RATIO_THRESHOLD = 0.02    # 2% max difference in normalized ratios (benchmark sanity check)

# Benchmark inputs (machine-readable, no JS scraping)
SILVER_FUTURES = "SI=F"   # Silver futures (USD per troy ounce)
USDINR = "USDINR=X"       # USD/INR FX rate

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]


TROY_OUNCE_G = 31.1034768  # grams in 1 troy ounce


# ---------------- HELPERS ----------------
def send_telegram(text: str) -> None:
    """
    Sends Telegram message if BOT_TOKEN is set.
    If BOT_TOKEN is empty, prints the message instead (so code still "works").
    """
    if not BOT_TOKEN:
        print("\n--- BOT_TOKEN empty: would send Telegram message below ---")
        print(text)
        print("--- end message ---\n")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    r = requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=20)
    r.raise_for_status()


def last_price(ticker: str) -> float:
    """
    Robust last price fetch using yfinance:
    - try fast_info["last_price"]
    - fallback to last close from 1m interval data
    """
    t = yf.Ticker(ticker)

    price = None
    try:
        price = t.fast_info.get("last_price")
    except Exception:
        price = None

    if price is None:
        hist = t.history(period="1d", interval="1m")
        if hist.empty:
            raise RuntimeError(f"No data for {ticker}")
        price = float(hist["Close"].iloc[-1])

    return float(price)


def silver_benchmark_inr_per_gm() -> float:
    """
    Benchmark silver price in INR per gram:
      (SI=F USD/oz * USDINR INR/USD) / 31.1034768 g/oz
    """
    silver_usd_per_oz = last_price(SILVER_FUTURES)
    usdinr = last_price(USDINR)

    inr_per_gm = (silver_usd_per_oz * usdinr) / TROY_OUNCE_G
    return float(inr_per_gm)


# ---------------- MAIN ----------------
def main():
    groww = last_price(TICKER_A)
    silver_etf = last_price(TICKER_B)
    etf_diff = groww - silver_etf

    bench_gm = silver_benchmark_inr_per_gm()

    # Unit-consistent validation:
    # Normalize both ETFs by the same benchmark (dimensionless ratios)
    groww_ratio = groww / bench_gm
    silver_ratio = silver_etf / bench_gm
    ratio_diff = abs(groww_ratio - silver_ratio)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Debug print (always)
    print(
        "GROWWSLVR:", round(groww, 4),
        "SILVERIETF:", round(silver_etf, 4),
        "ETF diff:", round(etf_diff, 6),
        "Benchmark (INR/gm):", round(bench_gm, 6),
        "GROWW ratio:", round(groww_ratio, 6),
        "SILVER ratio:", round(silver_ratio, 6),
        "Ratio diff:", round(ratio_diff, 6),
        "ETF threshold:", THRESHOLD,
        "Ratio threshold:", RATIO_THRESHOLD,
    )

    # Alert only if:
    # 1) ETF-vs-ETF gap is big enough, AND
    # 2) Both ETFs are behaving consistently vs benchmark (sanity check)
    if abs(etf_diff) > THRESHOLD and ratio_diff < RATIO_THRESHOLD:
        direction = (
            "GROWWSLVR higher than SILVERIETF"
            if etf_diff > 0
            else "SILVERIETF higher than GROWWSLVR"
        )

        msg = (
            "🚨 Silver ETF Alert (Benchmark-validated)\n\n"
            f"GROWWSLVR: {groww:.2f}\n"
            f"SILVERIETF: {silver_etf:.2f}\n"
            f"ETF Difference: {etf_diff:.2f}\n"
            f"Direction: {direction}\n\n"
            f"Benchmark (SI=F * USDINR) ₹/gm: {bench_gm:.2f}\n"
            f"GROWW ratio: {groww_ratio:.4f}\n"
            f"SILVER ratio: {silver_ratio:.4f}\n"
            f"Ratio diff: {ratio_diff:.4f} (must be < {RATIO_THRESHOLD:.4f})\n\n"
            f"⏱ {now}"
        )

        send_telegram(msg)
    else:
        # Explain why no alert (useful while tuning thresholds)
        reasons = []
        if abs(etf_diff) <= THRESHOLD:
            reasons.append(f"ETF gap not large enough: |{etf_diff:.4f}| <= {THRESHOLD}")
        if ratio_diff >= RATIO_THRESHOLD:
            reasons.append(f"Benchmark sanity check failed: {ratio_diff:.4f} >= {RATIO_THRESHOLD}")
        print("No alert:", " | ".join(reasons))


if __name__ == "__main__":
    main()
