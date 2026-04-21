"""
Clothing Recommendation Module
"""


def get_clothing_recommendation(weather):
    """Generate clothing recommendation based on weather data."""
    temp = weather.get("temp", 20)
    feels_like = weather.get("feels_like", temp)
    main = weather.get("main", "Clear")
    description = weather.get("description", "").lower()
    wind_speed = weather.get("wind_speed", 0)

    effective_temp = feels_like if feels_like is not None else temp

    items = []
    tips = []

    # Temperature-based suggestions
    if effective_temp < 0:
        items = ["Heavy down coat", "Thermal underwear", "Thick sweater",
                 "Thermal pants", "Warm hat", "Scarf", "Gloves", "Insulated boots"]
        tips.append("Freezing cold! Bundle up heavily.")
    elif effective_temp < 10:
        items = ["Wool coat or down jacket", "Long-sleeve shirt", "Sweater",
                 "Long pants", "Scarf", "Warm hat", "Boots"]
        tips.append("Quite cold — wear warm layers.")
    elif effective_temp < 18:
        items = ["Light jacket or hoodie", "Long-sleeve shirt",
                 "Long pants", "Closed shoes"]
        tips.append("Cool weather — bring a jacket.")
    elif effective_temp < 25:
        items = ["T-shirt or blouse", "Pants or jeans", "Sneakers"]
        tips.append("Mild and pleasant — dress comfortably.")
    elif effective_temp < 32:
        items = ["Light t-shirt", "Shorts or light trousers", "Breathable shoes"]
        tips.append("Warm — keep it light and breathable.")
    else:
        items = ["Minimal light clothing", "Shorts or thin skirt",
                 "Sandals", "Sun hat"]
        tips.append("Very hot — stay shaded and hydrated.")

    # Weather condition adjustments
    if main in ["Rain", "Drizzle"] or "rain" in description:
        items += ["Umbrella", "Waterproof jacket", "Waterproof shoes"]
        tips.append("Rain expected — don't forget your umbrella!")
    elif main == "Thunderstorm":
        items += ["Umbrella", "Waterproof jacket", "Waterproof shoes"]
        tips.append("Thunderstorms likely. Stay safe.")
    elif main == "Snow":
        items += ["Heavy winter coat", "Warm hat", "Gloves", "Waterproof boots"]
        tips.append("Snowy conditions — dress warmly.")
    elif main == "Clear" and effective_temp > 25:
        items += ["Sunglasses", "Sunscreen"]
    elif main in ["Mist", "Fog", "Haze"]:
        tips.append("Low visibility — be careful outdoors.")

    # Wind adjustment
    if wind_speed > 10:
        items.append("Windbreaker")
        tips.append("Strong winds — hold onto your hat!")

    # Remove duplicates
    seen = set()
    clean_items = []
    for item in items:
        if item.lower() not in seen:
            seen.add(item.lower())
            clean_items.append(item)

    return {"items": clean_items, "tips": tips}


def get_forecast_recommendation(day_forecast):
    """Short recommendation for a forecast day."""
    temp_min = day_forecast.get("temp_min", 20)
    temp_max = day_forecast.get("temp_max", 20)
    description = day_forecast.get("description", "Clear")

    avg = (temp_min + temp_max) / 2

    if avg < 0:
        base = "Heavy winter gear"
    elif avg < 10:
        base = "Warm coat & layers"
    elif avg < 18:
        base = "Light jacket"
    elif avg < 25:
        base = "Comfortable casual"
    elif avg < 32:
        base = "Light summer wear"
    else:
        base = "Minimal, stay cool"

    if description in ["Rain", "Drizzle"]:
        base += " + umbrella"
    elif description == "Thunderstorm":
        base += " + rain gear"
    elif description == "Snow":
        base += " + snow boots"
    elif description == "Clear" and avg > 28:
        base += " + sun protection"

    return base


def format_recommendation_html(rec):
    """Format recommendation for Streamlit display."""
    html = f"<p>👔 <b>Suggest:</b> {', '.join(rec['items'])}</p>"
    if rec["tips"]:
        html += f"<p>💡 <b>Tips:</b> {' '.join(rec['tips'])}</p>"
    return html
