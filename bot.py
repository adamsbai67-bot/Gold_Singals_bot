import os
import time
import requests
from datetime import datetime

# ═══════════════════════════════════════════
# CONFIGURATION — بدل هاد القيم
# ═══════════════════════════════════════════
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
TWELVEDATA_KEY = os.environ.get("TWELVEDATA_KEY", "")

SYMBOL = "XAU/USD"       # الذهب
INTERVAL = "5min"        # فريم 5 دقائق
CHECK_EVERY = 300        # كل 5 دقائق

# ═══════════════════════════════════════════
# TELEGRAM
# ═══════════════════════════════════════════
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

# ═══════════════════════════════════════════
# DATA
# ═══════════════════════════════════════════
def get_prices():
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": SYMBOL,
        "interval": INTERVAL,
        "outputsize": 250,
        "apikey": TWELVEDATA_KEY
    }
    r = requests.get(url, params=params, timeout=15)
    data = r.json()
    if "values" not in data:
        print(f"API error: {data}")
        return None
    # الأسعار من الأحدث للأقدم → نقلبهم
    values = list(reversed(data["values"]))
    return [float(v["close"]) for v in values]

# ═══════════════════════════════════════════
# INDICATORS
# ═══════════════════════════════════════════
def ema(prices, period):
    if len(prices) < period:
        return None
    k = 2 / (period + 1)
    e = sum(prices[:period]) / period
    for p in prices[period:]:
        e = p * k + e * (1 - k)
    return e

def rsi(prices, period=14):
    if len(prices) < period + 1:
        return None
    gains, losses = 0, 0
    for i in range(1, period + 1):
        diff = prices[i] - prices[i - 1]
        if diff > 0:
            gains += diff
        else:
            losses -= diff
    avg_gain = gains / period
    avg_loss = losses / period
    for i in range(period + 1, len(prices)):
        diff = prices[i] - prices[i - 1]
        gain = diff if diff > 0 else 0
        loss = -diff if diff < 0 else 0
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# ═══════════════════════════════════════════
# SIGNAL
# ═══════════════════════════════════════════
last_signal = None

def check_signal():
    global last_signal
    prices = get_prices()
    if not prices or len(prices) < 200:
        return

    price = prices[-1]
    e50 = ema(prices, 50)
    e200 = ema(prices, 200)
    r = rsi(prices, 14)

    if e50 is None or e200 is None or r is None:
        return

    signal = None
    reason = ""

    # BUY: EMA50 فوق EMA200 + RSI فوق 50 + السعر فوق EMA50
    if e50 > e200 and r > 50 and price > e50:
        signal = "BUY"
        reason = f"EMA50 > EMA200، RSI = {r:.1f}، السعر فوق EMA50"
    # SELL: EMA50 تحت EMA200 + RSI تحت 50 + السعر تحت EMA50
    elif e50 < e200 and r < 50 and price < e50:
        signal = "SELL"
        reason = f"EMA50 < EMA200، RSI = {r:.1f}، السعر تحت EMA50"

    if signal and signal != last_signal:
        last_signal = signal
        emoji = "🟢" if signal == "BUY" else "🔴"
        msg = (
            f"{emoji} <b>{signal} — {SYMBOL}</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💵 السعر: <b>{price:.2f}</b>\n"
            f"📊 RSI: <b>{r:.1f}</b>\n"
            f"📈 EMA50: {e50:.2f}\n"
            f"📉 EMA200: {e200:.2f}\n"
            f"⏰ {datetime.now().strftime('%H:%M')}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📝 {reason}\n"
            f"⚠️ راجع الشارت قبل الدخول"
        )
        print(f"[SIGNAL] {signal} @ {price}")
        send_telegram(msg)
    elif signal is None:
        last_signal = None  # نسمح بإشارة جديدة

# ═══════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════
def main():
    print(f"Bot started — {SYMBOL} {INTERVAL}")
    send_telegram(
        f"🤖 <b>بوت الإشارات شغال</b>\n"
        f"الزوج: {SYMBOL}\n"
        f"الفريم: {INTERVAL}\n"
        f"الفحص كل {CHECK_EVERY//60} دقائق"
    )
    while True:
        try:
            check_signal()
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(CHECK_EVERY)

if __name__ == "__main__":
    main()
