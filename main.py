import os, time, requests, warnings
import pandas as pd
warnings.filterwarnings('ignore')

TOKEN = "8241825240:AAEougyCwe3G8Qvrl5ab48qDOwX8j6jVdb0"
CHAT_ID = "2033758503"

SYMBOLS = {
    "EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD", "USDJPY=X": "USD/JPY",
    "AUDUSD=X": "AUD/USD", "USDCAD=X": "USD/CAD", "USDCHF=X": "USD/CHF",
    "NZDUSD=X": "NZD/USD", "EURGBP=X": "EUR/GBP", "EURJPY=X": "EUR/JPY",
    "GBPJPY=X": "GBP/JPY", "EURCHF=X": "EUR/CHF", "AUDJPY=X": "AUD/JPY",
    "GBPAUD=X": "GBP/AUD", "GBPCAD=X": "GBP/CAD", "GBPCHF=X": "GBP/CHF",
    "EURAUD=X": "EUR/AUD", "EURCAD=X": "EUR/CAD", "EURNZD=X": "EUR/NZD",
    "AUDCAD=X": "AUD/CAD", "AUDCHF=X": "AUD/CHF", "AUDNZD=X": "AUD/NZD",
    "CADJPY=X": "CAD/JPY", "CADCHF=X": "CAD/CHF", "CHFJPY=X": "CHF/JPY"
}

STAT_WIN = 0
STAT_LOSS = 0

def send_tg_keyboard(text):
    url = f"https://telegram.org{TOKEN}/sendMessage"
    kb = {"keyboard": [[{"text": "🟢 ЗАПУСТИТЬ ИИ"}, {"text": "🛑 СТОП"}],[{"text": "📊 СТАТУС РАБОТЫ"}]], "resize_keyboard": True}
    try: requests.post(url, json={"chat_id": str(CHAT_ID), "text": str(text), "reply_markup": kb}, timeout=5)
    except: pass

def send_tg_msg(text):
    url = f"https://telegram.org{TOKEN}/sendMessage"
    try:
        res = requests.post(url, json={"chat_id": str(CHAT_ID), "text": str(text)}, timeout=5).json()
        if res.get("ok"): return res["result"]["message_id"]
    except: pass
    return None

def edit_tg_msg(msg_id, text):
    url = f"https://telegram.org{TOKEN}/editMessageText"
    try: requests.post(url, json={"chat_id": str(CHAT_ID), "message_id": msg_id, "text": str(text)}, timeout=5)
    except: pass

def delete_tg_msg(msg_id):
    if not msg_id: return
    url = f"https://telegram.org{TOKEN}/deleteMessage"
    try: requests.post(url, json={"chat_id": str(CHAT_ID), "message_id": msg_id}, timeout=5)
    except: pass

def get_live_data(symbol, interval='1m'):
    try:
        url = f"https://yahoo.com{symbol}?interval={interval}&range=1d"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5).json()
        if 'chart' not in res or res['chart']['result'] is None or not res['chart']['result'].get('timestamp'):
            alt_symbol = symbol.replace("=X", "=OTC")
            url = f"https://yahoo.com{alt_symbol}?interval={interval}&range=1d"
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5).json()
        candles = res['chart']['result']['indicators']['quote']
        df = pd.DataFrame()
        df['close'] = candles['close']
        df['high'] = candles['high']
        df['low'] = candles['low']
        df['open'] = candles['open']
        df['time'] = res['chart']['result']['timestamp']
        return df.dropna()
    except: return pd.DataFrame()

def calculate_indicators(df):
    df['ema12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['stoch_k'] = 100 * ((df['close'] - df['low'].rolling(5).min()) / (df['high'].rolling(5).max() - df['low'].rolling(5).min()))
    return df

def run_scan():
    global STAT_WIN, STAT_LOSS
    for ticker, name in SYMBOLS.items():
        df_m1 = get_live_data(ticker, '1m')
        if df_m1.empty or len(df_m1) < 40: continue
        df_m1 = calculate_indicators(df_m1)
        row_m1 = df_m1.iloc[-1]
        closed_m1 = df_m1.iloc[-2]
        
        pre_call = (row_m1['close'] < row_m1['ema12'] and row_m1['stoch_k'] < 35)
        pre_put = (row_m1['close'] > row_m1['ema12'] and row_m1['stoch_k'] > 65)
        
        if pre_call or pre_put:
            dir_text = "ВВЕРХ (CALL) 🚀" if pre_call else "ВНИЗ (PUT) 📉"
            price_entry = row_m1['close']
            base_text = f"🔥 ИИ КОМАНДА: {dir_text}\n🌍 Валютная пара: {name} (OTC)\n⚙️ Цена входа: {price_entry:.5f}\n⏱ ЭКСПИРАЦИЯ: 2 МИНУТЫ"
            msg_id = send_tg_msg(base_text)
            
            if msg_id:
                time.sleep(110)
                df_check = get_live_data(ticker, '1m')
                if not df_check.empty:
                    price_exit = df_check.iloc[-1]['close']
                    if (pre_call and price_exit > price_entry) or (pre_put and price_exit < price_entry):
                        STAT_WIN += 1
                        edit_tg_msg(msg_id, f"🎯 СДЕЛКА ЗАВЕРШЕНА!\n🌍 Пара: {name}\n\n✅ ИТОГ СДЕЛКИ: ЧИСТЫЙ ПЛЮС !!!\n🛫 Вход: {price_entry:.5f} -> 🛬 Выход: {price_exit:.5f}")
                    else:
                        STAT_LOSS += 1
                        edit_tg_msg(msg_id, f"🎯 СДЕЛКА ЗАВЕРШЕНА!\n🌍 Пара: {name}\n\n❌ ИТОГ СДЕЛКИ: МИНУС (Примените Мартингейл)\n🛫 Вход: {price_entry:.5f} -> 🛬 Выход: {price_exit:.5f}")

def handler(request):
    """Служебный обработчик Vercel для мгновенного ответа серверу Telegram"""
    import json
    try:
        body = json.loads(request.body.read().decode('utf-8'))
        if "message" in body and "text" in body["message"]:
            text = body["message"]["text"]
            if text == "/start" or text == "📊 СТАТУС РАБОТЫ":
                send_tg_keyboard("💎 ИИ-Терминал v8.6 Высокой Частоты на Vercel активен!\n\nНажмите кнопку ниже:")
            elif text == "🟢 ЗАПУСТИТЬ ИИ":
                send_tg_keyboard("🟢 ИИ-Терминал вышел на высокочастотное сканирование рынка!")
                run_scan()
    except Exception as e:
        pass
    return {"statusCode": 200, "body": "OK"}
