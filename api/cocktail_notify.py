#!/usr/bin/env python3
"""
Рассылка уведомления о новом коктейле дня.
Запускается каждый день в 10:00 по Москве (07:00 UTC).
"""
import json
import os
import time
import urllib.request
import pymysql
import pymysql.cursors

BOT_TOKEN = os.getenv("BOT_TOKEN", "INVALID_TOKEN")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "zooparkbot")
DB_PASS = os.getenv("DB_PASS", "")
DB_NAME = os.getenv("DB_NAME", "zooparkbot")

FRUITS = ['🍓', '🫐', '🍏', '🍐', '🍇', '🍒']
TEXT = (
    "🥤 <b>Новый коктейль дня!</b>\n\n"
    "Сегодня появился новый секретный рецепт.\n"
    "Угадай комбинацию из 4 фруктов {fruits} за 10 попыток\n"
    "и забирай <b>150 🐾 PawCoins!</b>\n\n"
    "👆 Открой ZooPark → Игры → Коктейль"
).format(fruits=" ".join(FRUITS))


def send_message(chat_id: int, text: str) -> bool:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception:
        return False


def main():
    conn = pymysql.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor, charset="utf8mb4",
    )
    try:
        with conn.cursor() as cur:
            # Сбрасываем глобального победителя (новый день — новая игра)
            cur.execute(
                "UPDATE `values` SET value_str = NULL WHERE name = 'cocktail_daily_winner'"
            )
            conn.commit()

            # Берём всех незабаненных пользователей с tg_id
            cur.execute(
                "SELECT id_user FROM users WHERE COALESCE(is_banned, 0) = 0 AND id_user IS NOT NULL"
            )
            users = cur.fetchall()

        print(f"Рассылка {len(users)} пользователям...")
        ok = 0
        for row in users:
            tg_id = int(row["id_user"])
            if send_message(tg_id, TEXT):
                ok += 1
            time.sleep(0.05)  # ~20 сообщений/сек, не превышаем лимиты TG

        print(f"Отправлено: {ok}/{len(users)}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
