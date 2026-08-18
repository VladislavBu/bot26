import os, time, requests, warnings
import pandas as pd
warnings.filterwarnings('ignore')

TOKEN = os.environ.get("TOKEN", "8241825240:AAEougyCwe3G8Qvrl5ab48qDOwX8j6jVdb0")
CHAT_ID = os.environ.get("CHAT_ID", "2033758503")

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

BOT_ACTIVE = False
last_update_id = 0
active_alerts = {}
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
    df['ema26'] = df['close'].ewm(span=26, adjust=False).mean()
    df['bb_middle'] = df['close'].rolling(window=20).mean()
    df['bb_std'] = df['close'].rolling(window=20).std()
    df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * 2)
    df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * 2)
    low_5 = df['low'].rolling(window=5).min()
    high_5 = df['high'].rolling(window=5).max()
    df['stoch_k'] = 100 * ((df['close'] - low_5) / (high_5 - low_5))
    df['stoch_d'] = df['stoch_k'].rolling(window=3).mean()
    df['macd_hist'] = df['ema12'] - df['ema26']
    return df

print("ИИ Робот-Терминал v8.5 запущен!")

last_times = {ticker: None for ticker in SYMBOLS.keys()}

def handler(request):
    global BOT_ACTIVE, last_update_id, STAT_WIN, STAT_LOSS
    try:
        url_updates = f"https://telegram.org{TOKEN}/getUpdates?offset={last_update_id + 1}&limit=10"
        res_upd = requests.get(url_updates, timeout=5).json()
        if res_upd.get("ok") and res_upd.get("result"):
            for update in res_upd["result"]:
                last_update_id = update["update_id"]
                if "message" in update and "text" in update["message"]:
                    text = update["message"]["text"]
                    if text == "🟢 ЗАПУСТИТЬ ИИ":
                        BOT_ACTIVE = True
                        send_tg_keyboard("🟢 Высокочастотный ИИ-анализ 24 пар запущен!")
                    elif text == "🛑 СТОП":
                        BOT_ACTIVE = False
                        for t in list(active_alerts.keys()): delete_tg_msg(active_alerts[t]["msg_id"])
                        active_alerts.clear()
                        send_tg_keyboard("🛑 Сканирование полностью остановлено.")
                    elif text == "📊 СТАТУС РАБОТЫ" or text == "/start":
                        status = "🟢 АКТИВЕН" if BOT_ACTIVE else "🛑 НА ПАУЗЕ"
                        total = STAT_WIN + STAT_LOSS
                        rate = int((STAT_WIN / total) * 100) if total > 0 else 100
                        send_tg_keyboard(f"📊 Высокочастотный режим:\n• Статус: {status}\n\n📈 ТЕКУЩАЯ СЕССИЯ:\n✅ ПЛЮСЫ: {STAT_WIN}\n❌ МИНУСЫ: {STAT_LOSS}\n🎯 ВИНРЕЙТ: {rate}%")
    except: pass

    if BOT_ACTIVE:
        curr_ts = time.time()
        for t in list(active_alerts.keys()):
            if curr_ts - active_alerts[t]["time"] > 30:
                delete_tg_msg(active_alerts[t]["msg_id"])
                del active_alerts[t]

        for ticker, name in SYMBOLS.items():
            if not BOT_ACTIVE: break
            df_m1 = get_live_data(ticker, '1m')
            if df_m1.empty or len(df_m1) < 40: continue
            df_m1 = calculate_indicators(df_m1)
            row_m1 = df_m1.iloc[-1]
            closed_m1 = df_m1.iloc[-2]
            
            pre_call = (row_m1['close'] < row_m1['ema12'] and row_m1['stoch_k'] < 35)
            pre_put = (row_m1['close'] > row_m1['ema12'] and row_m1['stoch_k'] > 65)
            
            if (pre_call or pre_put) and ticker not in active_alerts:
                direction = "ВВЕРХ (CALL) 📈" if pre_call else "ВНИЗ (PUT) 📉"
                msg_id = send_tg_msg(f"⏳ ПРИГОТОВИТЬ ПАРУ: {name} (Forex / OTC)\n🧭 Направление: {direction}")
                if msg_id: active_alerts[ticker] = {"msg_id": msg_id, "time": curr_ts}
            
            current_time = closed_m1['time']
            if current_time != last_times[ticker]:
                call_signal = (closed_m1['close'] < closed_m1['ema12'] and closed_m1['stoch_k'] < 45)
                put_signal = (closed_m1['close'] > closed_m1['ema12'] and closed_m1['stoch_k'] > 65)
                
                if (call_signal or put_signal) and ticker in active_alerts:
                    delete_tg_msg(active_alerts[ticker]["msg_id"])
                    del active_alerts[ticker]
                    price_entry = closed_m1['close']
                    is_call = True if call_signal else False
                    dir_text = "ВВЕРХ (CALL) 🚀" if is_call else "ВНИЗ (PUT) 📉"
                    
                    base_text = f"🔥 ИИ КОМАНДА: {dir_text}\n🌍 Валютная пара: {name}\n⚙️ Цена входа: {price_entry:.5f}\n⏱ ЭКСПИРАЦИЯ: 2 МИНУТЫ"
                    msg_id = send_tg_msg(base_text)
                    if msg_id:
                        for left in range(120, -1, -10):
                            if left > 0:
                                mins, secs = left // 60, left % 60
                                edit_tg_msg(msg_id, f"{base_text}\n\n⏳ Сделка открыта! Осталось: {mins} мин {secs} ...")
                                time.sleep(10)
                            else:
                                time.sleep(5)
                                df_check = get_live_data(ticker, '1m')
                                if not df_check.empty:
                                    price_exit = df_check.iloc[-1]['close']
                                    if (is_call and price_exit > price_entry) or (not is_call and price_exit < price_entry):
                                        STAT_WIN += 1
                                        edit_tg_msg(msg_id, f"🎯 СДЕЛКА ЗАВЕРШЕНА!\n🌍 Пара: {name}\n\n✅ ИТОГ СДЕЛКИ: ЧИСТЫЙ ПЛЮС !!!\n🛫 Вход: {price_entry:.5f} -> 🛬 Выход: {price_exit:.5f}")
                                    else:
                                        STAT_LOSS += 1
                                        edit_tg_msg(msg_id, f"🎯 СДЕЛКА ЗАВЕРШЕНА!\n🌍 Пара: {name}\n\n❌ ИТОГ СДЕЛКИ: МИНУС (Примените Мартингейл)\n🛫 Вход: {price_entry:.5f} -> 🛬 Выход: {price_exit:.5f}")
                    last_times[ticker] = current_time
            time.sleep(0.1)
    return {"statusCode": 200, "body": "OK"}
