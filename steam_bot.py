import requests
import telebot
import time
import json
import os
from datetime import datetime

# ================================
# НАСТРОЙКИ — ИЗМЕНИ НА СВОИ!
# ================================

TELEGRAM_TOKEN = '8569974294:AAFXBa_KA5V8l3g5L3GKViaWMBdEchf6-Bo'  # ← Твой токен
TELEGRAM_CHANNEL = '@steam_kz_deals'  # ← Твой канал

# Файл для хранения уже опубликованных игр
SEEN_FILE = 'seen_steam_deals.json'

# ================================
# Инициализация
# ================================

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Загрузка списка уже опубликованных игр
if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE, 'r', encoding='utf-8') as f:
        seen = set(json.load(f))
else:
    seen = set()

# Список валют и их кодов
CURRENCIES = {
    'USD': 'us',
    'RUB': 'ru',
    'KZT': 'kz',
    'UAH': 'ua'
}

# ================================
# Функции
# ================================

def fetch_price(appid, country_code):
    """Получить цену игры в указанной валюте"""
    url = f'https://store.steampowered.com/api/appdetails'
    params = {
        'appids': appid,
        'cc': country_code,
        'filters': 'price_overview'
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            price_data = data.get(str(appid), {}).get('data', {}).get('price_overview', {})
            if price_data:
                return {
                    'original': price_data.get('initial_formatted', 'N/A'),
                    'discounted': price_data.get('final_formatted', 'N/A'),
                    'discount': price_data.get('discount_percent', 0)
                }
    except:
        pass
    return None

def save_seen():
    """Сохранить список опубликованных игр"""
    with open(SEEN_FILE, 'w', encoding='utf-8') as f:
        json.dump(list(seen), f, ensure_ascii=False, indent=2)

# ================================
# Основной цикл
# ================================

print(f"[{datetime.now()}] Бот запущен. Проверка каждые 60 минут...")

while True:
    try:
        print(f"[{datetime.now()}] Проверка новых скидок...")

        # Получаем список акционных игр с главной страницы Steam
        specials_url = 'https://store.steampowered.com/api/featuredcategories?cc=us'
        response = requests.get(specials_url, timeout=15)

        if response.status_code != 200:
            print("Ошибка подключения к Steam API")
            time.sleep(300)
            continue

        data = response.json()
        items = data.get('specials', {}).get('items', [])

        new_deals = 0
        for item in items[:10]:  # Берём только топ-10 акций
            appid = item.get('id')
            if not appid or appid in seen:
                continue

            name = item.get('name', 'Без названия')
            photo_url = item.get('large_capsule_image') or item.get('header_image')
            discount_percent = item.get('discount_percent', 0)

            if not photo_url:
                continue

            # Собираем цены по валютам
            prices = {}
            for currency, cc in CURRENCIES.items():
                price_data = fetch_price(appid, cc)
                if price_data:
                    prices[currency] = price_data
                else:
                    prices[currency] = {'original': 'N/A', 'discounted': 'N/A'}

            # Формируем текст
            lines = [f"🎮 *{name}*", f"💸 Скидка: {discount_percent}%"]
            for currency in CURRENCIES.keys():
                p = prices[currency]
                if p['original'] != 'N/A':
                    lines.append(f"*{currency}*: ~~{p['original']}~~ → **{p['discounted']}**")
                else:
                    lines.append(f"*{currency}*: Нет данных")

            caption = "\n".join(lines)

            # Отправляем в канал
            try:
                bot.send_photo(
                    chat_id=TELEGRAM_CHANNEL,
                    photo=photo_url,
                    caption=caption,
                    parse_mode='Markdown'
                )
                print(f"Опубликовано: {name}")

                # Добавляем в список опубликованных
                seen.add(appid)
                save_seen()
                new_deals += 1

                time.sleep(2)  # Чтобы не превысить лимиты Telegram
            except Exception as e:
                print(f"Ошибка отправки: {e}")

        if new_deals == 0:
            print("Новых скидок не найдено.")
        else:
            print(f"Опубликовано {new_deals} новых скидок.")

        # Ждём 1 час
        time.sleep(3600)

    except KeyboardInterrupt:
        print("\nБот остановлен пользователем.")
        break
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        time.sleep(300)  # 5 минут при ошибке