"""
SMS Service Module
Uses Submail API to send weather SMS.
"""

import requests

# ========== Submail Config (fill in your own) ==========
SUBMAIL_APPID = ""
SUBMAIL_APPKEY = ""

# API endpoints
SMS_URL = "https://api-v4.mysubmail.com/sms/send"
INTL_SMS_URL = "https://api-v4.mysubmail.com/internationalsms/send"


def send_sms(to_number, message):
    """
    Send SMS to a phone number using Submail.
    Returns a dict with success status and message.
    """
    # Demo mode if credentials are not set
    if not SUBMAIL_APPID or not SUBMAIL_APPKEY:
        return {
            "success": True,
            "demo": True,
            "message": "Demo mode - Submail not configured. SMS preview shown.",
            "preview": message
        }

    # Add SMS signature (required by Submail domestic SMS)
    content = "【WeatherWiseBot】" + message

    # Choose API: international numbers use + prefix except +86
    if to_number.startswith("+") and not to_number.startswith("+86"):
        url = INTL_SMS_URL
    else:
        url = SMS_URL
        # remove +86 prefix for domestic API
        if to_number.startswith("+86"):
            to_number = to_number[3:]

    data = {
        "appid": SUBMAIL_APPID,
        "signature": SUBMAIL_APPKEY,
        "to": to_number,
        "content": content,
        "sign_type": "normal"
    }

    try:
        response = requests.post(url, data=data, timeout=10)
        result = response.json()

        if result.get("status") == "success":
            return {
                "success": True,
                "demo": False,
                "message": f"SMS sent! ID: {result.get('send_id', 'N/A')}"
            }
        else:
            return {
                "success": False,
                "demo": False,
                "message": f"Submail error: {result.get('msg', 'Unknown error')}"
            }
    except Exception as e:
        return {
            "success": False,
            "demo": False,
            "message": f"Failed to send SMS: {str(e)}"
        }


def build_weather_sms(weather, forecast=None, alerts=None, rec=None, include_weather=True):
    """
    Build a weather report SMS text from weather data.
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
