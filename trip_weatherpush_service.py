"""
Trip Weather Push Service Module
Handles trip weather report generation and scheduled push logic.
"""

import threading
import time
from datetime import datetime

from weather_service import get_weather
from recommendation import get_clothing_recommendation
from telegram_service import send_telegram


# ==================== Message Builder ====================

def build_trip_weather_message(dep_weather, dep_rec, dep_time, arr_weather, arr_rec, arr_time):
    """Build a trip weather report message for Telegram."""
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


# ==================== Scheduled Push Worker ====================

def scheduled_push_worker(session_state_ref, chat_id, dep_city, arr_city, push_time):
    """
    Background worker for scheduled daily trip weather push.
    
    Args:
        session_state_ref: A dict-like object (e.g., st.session_state) to read 'scheduled_push_active'.
        chat_id: Telegram Chat ID.
        dep_city: Departure city name.
        arr_city: Arrival city name.
        push_time: datetime.time object specifying when to push each day.
    """
    while session_state_ref.get("scheduled_push_active", False):
        now = datetime.now()
        # Check if current time matches push time (within same minute)
        if now.hour == push_time.hour and now.minute == push_time.minute:
            try:
                dep_weather = get_weather(dep_city)
                arr_weather = get_weather(arr_city)

                if dep_weather and arr_weather:
                    dep_rec = get_clothing_recommendation(dep_weather)
                    arr_rec = get_clothing_recommendation(arr_weather)

                    message = build_trip_weather_message(
                        dep_weather, dep_rec, now,
                        arr_weather, arr_rec, now
                    )
                    send_telegram(chat_id, message)
            except Exception as e:
                print(f"Scheduled push error: {e}")

            # Sleep 61 seconds to avoid duplicate sends in the same minute
            time.sleep(61)
        else:
            time.sleep(30)


# ==================== Instant Push Service ====================

def send_trip_weather_report(chat_id, departure_city, departure_time, arrival_city, arrival_time):
    """
    Fetch weather for departure and arrival cities, build trip report, and send via Telegram.
    
    Returns:
        dict: {"success": bool, "message": str, "preview": str (optional)}
    """
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


# ==================== Scheduled Push Controller ====================

def start_scheduled_push(session_state_ref, chat_id, dep_city, arr_city, push_time):
    """
    Start a background thread for scheduled daily trip weather push.
    
    Returns:
        threading.Thread: The started daemon thread.
    """
    session_state_ref["scheduled_push_active"] = True
    thread = threading.Thread(
        target=scheduled_push_worker,
        args=(session_state_ref, chat_id, dep_city, arr_city, push_time),
        daemon=True
    )
    thread.start()
    return thread


def stop_scheduled_push(session_state_ref):
    """Stop the scheduled push by setting the active flag to False."""
    session_state_ref["scheduled_push_active"] = False
