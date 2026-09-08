# -*- coding: utf-8 -*-
import os
import time
import json
import threading
import urllib.request
from flask import Flask
import telebot

# --- RENDER ÜÇÜN FLASK SERVERİ (7/24 DİRİ SAXLAMAQ ÜÇÜN) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot status: Active"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# --- TELEGRAM BOT QURULUSHLARI ---
TOKEN = os.environ.get('BOT_TOKEN', 'YOUR_TELEGRAM_BOT_TOKEN_HERE')
bot = telebot.TeleBot(TOKEN)

# --- INDIKATOR HESABLAMALARI ---
def calculate_indicators(prices):
    if len(prices) < 35:
        return None

    close = prices
    high = prices  # YF sadə massiv verdiyi üçün yaxınlaşma istifadə olunur
    low = prices

    # 1. Stochastic Oscillator (14, 3, 3)
    low_14 = min(low[-14:])
    high_14 = max(high[-14:])
    stoch_k = 50
    if high_14 != low_14:
        stoch_k = ((close[-1] - low_14) / (high_14 - low_14)) * 100

    # 2. CCI (Commodity Channel Index - 20)
    tp = close[-1]
    sma_tp = sum(close[-20:]) / 20
    mean_dev = sum(abs(x - sma_tp) for x in close[-20:]) / 20
    cci = 0
    if mean_dev != 0:
        cci = (tp - sma_tp) / (0.015 * mean_dev)

    # 3. MACD (12, 26, 9)
    ema12 = sum(close[-12:]) / 12
    ema26 = sum(close[-26:]) / 26
    macd_line = ema12 - ema26

    # 4. Parabolic SAR (Sada Trend Təsdiqi)
    psar_up = close[-1] > close[-3]

    # --- SƏSVERMƏ VƏ TƏHLİL ---
    score = 0

    # Stochastic Səsverməsi
    if stoch_k < 20: score += 1      # Call
    elif stoch_k > 80: score -= 1    # Put

    # CCI Səsverməsi
    if cci < -100: score += 1        # Call
    elif cci > 100: score -= 1       # Put

    # MACD Səsverməsi
    if macd_line > 0: score += 1     # Call
    elif macd_line < 0: score -= 1    # Put

    # Parabolic SAR Səsverməsi
    if psar_up: score += 1           # Call
    else: score -= 1                 # Put

    # Qərar
    if score >= 3:
        return "🟢 **CALL (YUXARI)**\n\n*Təhlil:* 4 indikatordan minimum 3-ü YUXARI hərəkət göstərir."
    elif score <= -3:
        return "🔴 **PUT (AŞAĞI)**\n\n*Təhlil:* 4 indikatordan minimum 3-ü AŞAĞI hərəkət göstərir."
    else:
        return "⚠️ **GÖZLƏYİN (NEUTRAL)**\n\n*Təhlil:* Indikatorlar arasında ziddiyyət var, risk etməyin."

# --- YAHOO FINANCE DATA ÇƏKMƏK ---
def get_market_analysis(symbol="EURUSD=X"):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1m&range=1d"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req)
        data = json.loads(response.read().decode())
        prices = data['chart']['result'][0]['indicators']['quote'][0]['close']
        valid_prices = [p for p in prices if p is not None]
        
        return calculate_indicators(valid_prices)
    except Exception as e:
        return f"Xəta baş verdi: {str(e)}"

# --- TELEGRAM BOT ƏMRƏLƏRİ ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Salam! Binar opsion analiz botuna xoş gəldiniz.\nSiqnal almaq üçün valyuta cütlüyünü seçin və ya /signal yazın.")

@bot.message_handler(commands=['signal'])
def send_signal(message):
    msg = bot.reply_to(message, "📊 4 Indikator üzrə bazar təhlil olunur...")
    result = get_market_analysis("EURUSD=X")
    bot.edit_message_text(result, chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")

if __name__ == '__main__':
    t = threading.Thread(target=run_flask)
    t.start()
    bot.infinity_polling()
