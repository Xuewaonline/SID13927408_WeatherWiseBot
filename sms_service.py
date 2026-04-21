"""
SMS Service Module
Uses Twilio API to send weather SMS.
"""

import requests

# Twilio Config (fill in your own)
TWILIO_SID = "AC48868ecb9832a0777758436c57dd4553"
TWILIO_TOKEN = "9e32487246ab97ad602b8ec9fc2b315c"
TWILIO_FROM = "+17348212752"


def send_sms(to_number, message):
    """
    Send SMS to a phone number.
    Returns a dict with success status and message.
    """
    # Demo mode if credentials are not set
    if not TWILIO_SID or not TWILIO_TOKEN or not TWILIO_FROM:
        return {
            "success": True,
            "demo": True,
            "message": "Demo mode - Twilio not configured. SMS preview shown.",
            "preview": message
        }

    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"

    try:
        response = requests.post(
            url,
            data={"To": to_number, "From": TWILIO_FROM, "Body": message},
            auth=(TWILIO_SID, TWILIO_TOKEN),
            timeout=10
        )
        result = response.json()

        if response.status_code == 201:
            return {
                "success": True,
                "demo": False,
                "message": f"SMS sent! SID: {result.get('sid', 'N/A')}"
            }
        else:
            return {
                "success": False,
                "demo": False,
                "message": f"Twilio error: {result.get('message', 'Unknown error')}"
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
