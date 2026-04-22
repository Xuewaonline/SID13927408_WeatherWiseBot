"""
Telegram Bot Service Module
Send weather notifications via Telegram Bot API.
"""

import requests

# ========== Telegram Config ==========
TELEGRAM_BOT_TOKEN = "8607118945:AAGuBqszWuN3N-4gtSkU3nQjzA3fCosnYaA"

def send_telegram(chat_id, message):
    """
    Send message to a Telegram chat using Bot API.
    """
    # Demo mode if token is not set
    if not TELEGRAM_BOT_TOKEN:
        return {
            "success": True,
            "demo": True,
            "message": "Demo mode - Telegram Bot not configured. Message preview shown.",
            "preview": message
        }

    if not chat_id:
        return {
            "success": False,
            "message": "Please enter a Telegram Chat ID."
        }

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message
    }

    try:
        response = requests.post(url, data=data, timeout=10)
        result = response.json()

        if result.get("ok"):
            return {
                "success": True,
                "demo": False,
                "message": "Message sent to Telegram!"
            }
        else:
            return {
                "success": False,
                "demo": False,
                "message": f"Telegram error: {result.get('description', 'Unknown error')}"
            }
    except Exception as e:
        return {
            "success": False,
            "demo": False,
            "message": f"Failed to send message: {str(e)}"
        }


def build_weather_message(weather, forecast=None, alerts=None, rec=None, include_weather=True):
    """
    Build a weather report message from weather data.
    """
    lines = []

    if include_weather:
        lines.append(f"Weather in {weather['city']}:")
        lines.append(f"Temp: {weather['temp']}C (feels like {weather['feels_like']}C)")
        lines.append(f"Condition: {weather['description']}")
        lines.append(f"Humidity: {weather['humidity']}%, Wind: {weather['wind_speed']}m/s")

    if rec and rec.get("items"):
        lines.append(f"Outfit: {', '.join(rec['items'][:3])}")

    if alerts:
        for a in alerts:
            lines.append(f"Alert: {a['message']}")

    if forecast:
        lines.append("Forecast:")
        for day in forecast[:3]:
            lines.append(f"  {day['weekday']}: {day['temp_min']}-{day['temp_max']}C")

    return "\n".join(lines)
