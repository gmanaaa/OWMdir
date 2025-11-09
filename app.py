from datetime import datetime, timedelta, timezone
import requests
from linebot import LineBotApi
from linebot.models import TextSendMessage
import csv
import os

# --- APIキーなど ---
OWM_API_KEY = "14b2207eef84ff02be926443b06e59c7"
LAT, LON = 33.59, 130.40  # 福岡市
JST = timezone(timedelta(hours=9))

LINE_CHANNEL_ACCESS_TOKEN = "euab5FPZjIPMHwqeulO/lfCdqsALRRhQFkrMfcq4ZFaEr9boRb4Q4UHBMj1X8u1Yzex+y6enMGlTknokTBnJhN7EhRxnEWu3307g+l40wAIFPv4xb3uo6rFvtDid7ae7sUrZdGo4qFGbnQE8GJEkDwdB04t89/1O/w1cDnyilFU="
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)


# --- 共通: OWMから予報取得 ---OWM の「5日間/3時間ごとの予報 API」を叩いて JSON データを返す。---
def get_forecast():
    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {
        "lat": LAT,
        "lon": LON,
        "appid": OWM_API_KEY,
        "units": "metric",
        "lang": "ja"
    }
    return requests.get(url, params=params).json()


# --- ① 明日の降水確率通知 ---明日の予報の中から「降水確率30%以上」の時間帯を抽出。---
def notify_rain_forecast(data):
    tomorrow = (datetime.now(JST) + timedelta(days=1)).date()
    rainy_slots = []

    for item in data["list"]:
        dt = datetime.utcfromtimestamp(item["dt"]).replace(tzinfo=timezone.utc).astimezone(JST)
        if dt.date() == tomorrow:
            pop = item.get("pop", 0) * 100
            if pop >= 30:
                rainy_slots.append(f"{dt.strftime('%H:%M')} 降水確率 {pop:.0f}%")

    if rainy_slots:
        message = "明日の福岡は以下の時間帯で雨の可能性があります☔\n" + "\n".join(rainy_slots)
        line_bot_api.broadcast(TextSendMessage(text=message))
    else:
        # テスト用に通知（本番では送らない）
        line_bot_api.broadcast(TextSendMessage(text="明日は雨の心配はなさそうです😊"))


# --- ② 今日と明日の気温差通知 ---今日と明日の気温データを集めて平均を計算。---
def notify_temp_difference(data):
    now = datetime.now(JST)
    today = now.date()
    tomorrow = (now + timedelta(days=1)).date()

    temps_today, temps_tomorrow = [], []

    for item in data["list"]:
        dt = datetime.utcfromtimestamp(item["dt"]).replace(tzinfo=timezone.utc).astimezone(JST)
        if dt.date() == today:
            temps_today.append(item["main"]["temp"])
        elif dt.date() == tomorrow:
            temps_tomorrow.append(item["main"]["temp"])

    if temps_today and temps_tomorrow:
        avg_today = sum(temps_today) / len(temps_today)
        avg_tomorrow = sum(temps_tomorrow) / len(temps_tomorrow)
        diff = avg_tomorrow - avg_today

        # 蓄積
        save_temps(today, avg_today)
        save_temps(tomorrow, avg_tomorrow)

        if abs(diff) >= 5:
            message = f"今日と明日の平均気温差は {diff:.1f}℃ です！体調管理に注意してください。"
            line_bot_api.broadcast(TextSendMessage(text=message))
        else:
            line_bot_api.broadcast(TextSendMessage(text="明日との寒暖差は5℃未満なので安心です😊"))


# --- ③ 気温をCSVに蓄積 ---日付と平均気温を temps.csv に追記。---
def save_temps(date, avg_temp):
    filename = "temps.csv"
    file_exists = os.path.isfile(filename)

    with open(filename, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["date", "avg_temp"])
        writer.writerow([date.isoformat(), f"{avg_temp:.1f}"])


# --- メイン処理 ---
if __name__ == "__main__":
    forecast = get_forecast()
    notify_rain_forecast(forecast)
    notify_temp_difference(forecast)
