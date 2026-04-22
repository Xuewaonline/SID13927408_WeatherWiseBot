"""
Weather Service Module
"""

import json
import ssl
import urllib.request
from datetime import datetime

API_KEY = "613aaacbc3bcc47661a683c62d2e03d2"

# ==================== Main Functions ====================

def get_weather(city):
    city = city.strip().title()
    
    # Build API URL
    url = "https://api.openweathermap.org/data/2.5/weather"
    
    # Request parameters
    params = {
        "q": city,
        "appid": API_KEY,
        "units": "metric",
        "lang": "en"
    }
    
    try:
        # Send request to weather API
        data = http_get_json(url, params)
        
        # Check if city was found
        if data.get("cod") != 200:
            print(f"City not found: {city}")
            return None
        
        # Extract weather information from response
        weather = {
            "city": data["name"],
            "country": data["sys"]["country"],
            "temp": round(data["main"]["temp"]),
            "feels_like": round(data["main"]["feels_like"]),
            "humidity": data["main"]["humidity"],
            "description": data["weather"][0]["description"],
            "main": data["weather"][0]["main"],
            "wind_speed": data["wind"]["speed"]
        }
        return weather
        
    except Exception as e:
        print(f"Error fetching weather for {city}: {e}")
        return None


def get_forecast(city):
    """
    Get 5-day weather forecast for a city
    """
    city = city.strip().title()
    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {
        "q": city,
        "appid": API_KEY,
        "units": "metric"
    }
    
    try:
        data = http_get_json(url, params)
        
        # Check if city was found
        if data.get("cod") != "200":
            print(f"City not found: {city}")
            return []
        
        # Group data by day
        days = {}
        for item in data["list"]:
            date = item["dt_txt"].split(" ")[0]  # Extract date part
            
            if date not in days:
                days[date] = {"temps": [], "descriptions": []}
            
            days[date]["temps"].append(item["main"]["temp"])
            days[date]["descriptions"].append(item["weather"][0]["main"])
        
        # Build forecast list (first 5 days)
        forecast = []
        for date, values in list(days.items())[:5]:
            temps = values["temps"]
            descriptions = values["descriptions"]
            
            # Find most common weather condition
            most_common = max(set(descriptions), key=descriptions.count)
            
            forecast.append({
                "date": date,
                "weekday": get_weekday_name(date),
                "temp_min": round(min(temps)),
                "temp_max": round(max(temps)),
                "description": most_common
            })
        
        return forecast
        
    except Exception as e:
        print(f"Error fetching forecast for {city}: {e}")
        return []


def check_bad_weather(city):
    """
    Check for severe weather alerts
    """
    city = city.strip().title()
    weather = get_weather(city)
    
    # Return empty list if city not found
    if weather is None:
        return []
    
    alerts = []
    
    # Check for extreme heat
    if weather["temp"] > 35:
        alerts.append({
            "type": "Extreme Heat",
            "message": f"Temperature is {weather['temp']}°C. Stay cool and hydrated!"
        })
    
    # Check for extreme cold
    if weather["temp"] < 0:
        alerts.append({
            "type": "Extreme Cold",
            "message": f"Temperature is {weather['temp']}°C. Stay warm!"
        })
    
    # Check for rain
    if "rain" in weather["description"].lower():
        alerts.append({
            "type": "Rain Alert",
            "message": "Rain expected. Don't forget your umbrella!"
        })
    
    # Check for strong wind
    if weather["wind_speed"] > 10:
        alerts.append({
            "type": "Strong Wind",
            "message": f"Wind speed is {weather['wind_speed']} m/s. Be careful outdoors."
        })
    
    return alerts


# ==================== Helper Functions ====================

def http_get_json(url, params=None, timeout=10):
    """
    Send HTTP GET request and return JSON data
    """
    # Add parameters to URL if provided
    if params:
        query_parts = []
        for key, value in params.items():
            query_parts.append(f"{key}={urllib.request.quote(str(value))}")
        url = f"{url}?{'&'.join(query_parts)}"
    
    # Create request
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0'
    })
    
    # Create SSL context
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    # Send request and get response
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
        data = response.read().decode('utf-8')
        return json.loads(data)


def get_weekday_name(date_string):
    """
    Convert date string to weekday name
    """
    weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    date = datetime.strptime(date_string, "%Y-%m-%d")
    return weekdays[date.weekday()]


def get_weather_emoji(weather_main):
    """
    Get emoji for weather condition
    """
    emojis = {
        "Clear": "☀️",
        "Clouds": "☁️",
        "Rain": "🌧️",
        "Drizzle": "🌦️",
        "Thunderstorm": "⛈️",
        "Snow": "❄️",
        "Mist": "🌫️",
        "Fog": "🌫️",
        "Haze": "🌫️"
    }
    return emojis.get(weather_main, "🌤️")


def interactive_weather_query():
    """
    Interactive weather query - command line version
    """
    print("=" * 50)
    print("🌤️ WeatherWiseBot - Interactive Weather Query")
    print("=" * 50)
    print("Tips: Enter city name (English, case insensitive)")
    print("      Enter 'quit' or 'exit' to exit")
    print("=" * 50)
    
    while True:
        print()
        city = input("Enter city name > ").strip()
        
        # Check for exit
        if city.lower() in ['quit', 'exit', 'q']:
            print("\nThank you for using WeatherWiseBot! 👋")
            break
        
        # Check empty input
        if not city:
            print("⚠️ Please enter a valid city name")
            continue
        
        print(f"\nQuerying weather for '{city.title()}'...\n")
        
        # Get weather
        weather = get_weather(city)
        
        if weather is None:
            print(f"❌ City '{city}' not found. Please check the spelling.")
            continue
        
        # Display weather info
        emoji = get_weather_emoji(weather["main"])
        print(f"{emoji} {weather['city']}, {weather['country']}")
        print(f"   Temperature: {weather['temp']}°C (feels like {weather['feels_like']}°C)")
        print(f"   Weather: {weather['description']}")
        print(f"   Humidity: {weather['humidity']}%")
        print(f"   Wind Speed: {weather['wind_speed']} m/s")
        
        # Check alerts
        alerts = check_bad_weather(city)
        if alerts:
            print("\n⚠️ Weather Alerts:")
            for alert in alerts:
                print(f"   • {alert['type']}: {alert['message']}")
        
        # Ask for forecast
        print()
        show_forecast = input("Show 5-day forecast? (y/n) > ").strip().lower()
        if show_forecast in ['y', 'yes']:
            forecast = get_forecast(city)
            if forecast:
                print(f"\n📅 5-Day Forecast for {weather['city']}:")
                for day in forecast:
                    day_emoji = get_weather_emoji(day["description"])
                    print(f"   {day['weekday']}: {day['temp_min']}°C - {day['temp_max']}°C {day_emoji}")


# ==================== Test ====================
if __name__ == "__main__":
    # Check for command line arguments
    import sys
    
    if len(sys.argv) > 1:
        # Command line mode: python weather_service.py Beijing
        city = sys.argv[1]
        print(f"=== Weather for {city} ===\n")
        
        weather = get_weather(city)
        if weather:
            print(f"City: {weather['city']}, {weather['country']}")
            print(f"Temperature: {weather['temp']}°C (feels like {weather['feels_like']}°C)")
            print(f"Weather: {weather['description']}")
            print(f"Humidity: {weather['humidity']}%")
            print(f"Wind Speed: {weather['wind_speed']} m/s")
        else:
            print("Failed to get weather data")
    else:
        # Interactive mode
        interactive_weather_query()
