import requests
import yfinance as yf
from datetime import datetime

# ---- CONFIG ----
TICKER_A = "GROWWSLVR.NS"
TICKER_B = "SILVERIETF.NS"
THRESHOLD = 5.0  # absolute threshold

BOT_TOKEN = "8358559850:AAHMZPYuvgdI17OaK9sLgEmYG-8dPHI2_IQ"
CHAT_ID = "8418285542"


def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    r = requests.post(url, json={"chat_id": CHAT_ID, "text": text})
    r.raise_for_status()


def last_price(ticker: str) -> float:
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


def main():
    a = last_price(TICKER_A)
    b = last_price(TICKER_B)
    diff = a - b

    print("A:", a, "B:", b, "diff:", diff, "threshold:", THRESHOLD)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if abs(diff) > THRESHOLD:
        direction = (
            "GROWWSLVR higher than SILVERIETF"
            if diff > 0
            else "SILVERIETF higher than GROWWSLVR"
        )

        msg = (
            "🚨 Silver ETF Arbitrage Alert\n\n"
            f"GROWWSLVR: {a:.2f}\n"
            f"SILVERIETF: {b:.2f}\n"
            f"Difference: {diff:.2f}\n"
            f"Direction: {direction}\n\n"
            f"⏱ {now}"
        )

        send_telegram(msg)


if __name__ == "__main__":
    main()
