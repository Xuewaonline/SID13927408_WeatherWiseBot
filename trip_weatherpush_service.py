"""
Trip Weather Push Service Module
"""

from datetime import datetime

from weather_service import get_weather
from recommendation import get_clothing_recommendation
from telegram_service import send_telegram

# ==================== Message Builder ====================

def build_trip_weather_message(dep_weather, dep_rec, dep_time, arr_weather, arr_rec, arr_time):
    lines = []
    lines.append("🚗 Trip Weather Report")
    lines.append("")

    # Departure info
    lines.append(f"📍 Departure: {dep_weather['city']}")
    lines.append(f"🕐 Departure Time: {dep_time.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"🌡️ Temperature: {dep_weather['temp']}°C (feels like {dep_weather['feels_like']}°C)")
    lines.append(f"☁️ Condition: {dep_weather['description']}")
    lines.append(f"💧 Humidity: {dep_weather['humidity']}%, 💨 Wind: {dep_weather['wind_speed']}m/s")
    if dep_rec and dep_rec.get("items"):
        lines.append(f"👔 Outfit: {', '.join(dep_rec['items'][:4])}")
    lines.append("")

    # Arrival info
    lines.append(f"📍 Arrival: {arr_weather['city']}")
    lines.append(f"🕐 Arrival Time: {arr_time.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"🌡️ Temperature: {arr_weather['temp']}°C (feels like {arr_weather['feels_like']}°C)")
    lines.append(f"☁️ Condition: {arr_weather['description']}")
    lines.append(f"💧 Humidity: {arr_weather['humidity']}%, 💨 Wind: {arr_weather['wind_speed']}m/s")
    if arr_rec and arr_rec.get("items"):
        lines.append(f"👔 Outfit: {', '.join(arr_rec['items'][:4])}")

    return "\n".join(lines)



# ==================== Instant Push Service ====================

def send_trip_weather_report(chat_id, departure_city, departure_time, arrival_city, arrival_time):

    # Fetch departure weather
    dep_weather = get_weather(departure_city)
    if dep_weather is None:
        return {
            "success": False,
            "message": f"Departure city '{departure_city}' not found."
        }

    # Fetch arrival weather
    arr_weather = get_weather(arrival_city)
    if arr_weather is None:
        return {
            "success": False,
            "message": f"Arrival city '{arrival_city}' not found."
        }

    # Build recommendations
    dep_rec = get_clothing_recommendation(dep_weather)
    arr_rec = get_clothing_recommendation(arr_weather)

    # Build message
    message = build_trip_weather_message(
        dep_weather, dep_rec, departure_time,
        arr_weather, arr_rec, arrival_time
    )

    # Send Telegram
    return send_telegram(chat_id, message)


