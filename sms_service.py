"""
SMS Service Module
Uses Twilio API to send weather SMS.
"""

import urllib.request
import urllib.parse
import base64
import json
import ssl

# ========== Twilio Config (fill in your own) ==========
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
            "message": "Demo mode — Twilio not configured. SMS preview shown.",
            "preview": message
        }

    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"

    data = urllib.parse.urlencode({
        "To": to_number,
        "From": TWILIO_FROM,
        "Body": message
    }).encode()

    auth = base64.b64encode(f"{TWILIO_SID}:{TWILIO_TOKEN}".encode()).decode()

    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Basic {auth}")

    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        with urllib.request.urlopen(req, context=ctx) as response:
            result = json.loads(response.read().decode())
            return {
                "success": True,
                "demo": False,
                "message": f"SMS sent! SID: {result.get('sid', 'N/A')}"
            }
    except Exception as e:
        return {
            "success": False,
            "demo": False,
            "message": f"Failed to send SMS: {str(e)}"
        }


def build_weather_sms(weather, forecast=None, alerts=None, rec=None):
    """
    Build a weather report SMS text from weather data.
    """
    lines = [
        f"Weather in {weather['city']}:",
        f"Temp: {weather['temp']}C (feels like {weather['feels_like']}C)",
        f"Condition: {weather['description']}",
        f"Humidity: {weather['humidity']}%, Wind: {weather['wind_speed']}m/s"
    ]

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
