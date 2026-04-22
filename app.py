"""
WeatherWiseBot - Main Application

"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Import weather service and recommendation modules
from weather_service import get_weather, get_forecast, check_bad_weather, get_weather_emoji
from recommendation import get_clothing_recommendation, get_forecast_recommendation, format_recommendation_html
from telegram_service import send_telegram, build_weather_message

# ==================== Page Setup ====================

st.set_page_config(
    page_title="WeatherWiseBot",
    page_icon="🌤️",
    layout="wide"
)

# Initialize session state
if "current_city" not in st.session_state:
    st.session_state.current_city = "Hong Kong"

# ==================== Sidebar ====================

st.sidebar.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
st.sidebar.markdown("<h1 style='text-align: center; margin: 0; font-size: 1.8rem;'>🌤️<br>WeatherWiseBot</h1>", unsafe_allow_html=True)

# Navigation menu with emojis and larger font
st.sidebar.markdown("<br><br>", unsafe_allow_html=True)

if "nav_option" not in st.session_state:
    st.session_state.nav_option = "🏠 Home"

nav_options = ["🏠 Home", "🌦️ Weather Query", "📱 Telegram Push"]

for option in nav_options:
    if st.sidebar.button(option, use_container_width=True, 
                         type="primary" if st.session_state.nav_option == option else "secondary"):
        st.session_state.nav_option = option
        st.rerun()

page = st.session_state.nav_option.replace("🏠 ", "").replace("🌦️ ", "").replace("📱 ", "")

# ==================== Home Page ====================

def show_home():
    """Display home page"""
    st.title("🌤️ Welcome to WeatherWiseBot")
    st.write("🌷 Your personal weather assistant")
    
    st.markdown("---")

    # Feature cards with emojis
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("<h5 style='text-align: left; margin-bottom: 0.3rem;'>🌍 Global Coverage</h4>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: left; font-size: 1.25em; color: #555; font-weight: 500; margin-top: 0;'>Major Cities</p>", unsafe_allow_html=True)
        st.write("🏙️ Check weather in major cities worldwide")
    
    with col2:
        st.markdown("<h5 style='text-align: left; margin-bottom: 0.3rem;'>👔 Smart Outfit</h4>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: left; font-size: 1.25em; color: #555; font-weight: 500; margin-top: 0;'>Daily Tips</p>", unsafe_allow_html=True)
        st.write("🧥 Get clothing suggestions based on weather")
    
    with col3:
        st.markdown("<h5 style='text-align: left; margin-bottom: 0.3rem;'>📱 Telegram Notification</h4>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: left; font-size: 1.25em; color: #555; font-weight: 500; margin-top: 0;'>Instant</p>", unsafe_allow_html=True)
        st.write("📤 Send weather info via Telegram instantly")
    
    st.markdown("---")
    
    # Quick weather check
    st.subheader("Quick Weather Check")
    
    city = st.text_input("Enter city name (English)", st.session_state.current_city, key="home_city_input")
    
    if st.button("Get Weather"):
        weather = get_weather(city)
        
        if weather is None:
            st.error(f"❌ City '{city}' not found. Please check the spelling and try again.")
            return
        
        # Display weather
        col1, col2 = st.columns([2, 1])
        
        with col1:
            emoji = get_weather_emoji(weather["main"])
            st.success(f"""
            ### {emoji} {weather['city']}
            ## {weather['temp']}°C
            {weather['description']}
            """)
        
        with col2:
            st.write(f"Feels like: {weather['feels_like']}°C")
            st.write(f"Humidity: {weather['humidity']}%")
            st.write(f"Wind: {weather['wind_speed']} m/s")
        
        # Clothing recommendation
        rec = get_clothing_recommendation(weather)
        st.markdown("---")
        st.markdown(f"👔 **Smart Outfit Suggestion**")
        st.markdown(format_recommendation_html(rec), unsafe_allow_html=True)


# ==================== Telegram Push Page ====================

def show_telegram_send():
    """Display Telegram push page"""
    st.title("📱 Telegram Notification")
    
    st.subheader("Send Weather Report via Telegram")
    st.caption("Powered by Telegram @weatherwise_yukibot")
    
    col1, col2 = st.columns(2)
    with col1:
        city = st.text_input("City name", st.session_state.current_city, key="telegram_city")
    with col2:
        chat_id = st.text_input("Telegram Chat ID", "", key="telegram_chat_id")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        include_weather = st.checkbox("Current weather", True)
    with col2:
        include_forecast = st.checkbox("3-day forecast", True)
    with col3:
        include_outfit = st.checkbox("Outfit tip", True)
    with col4:
        include_alerts = st.checkbox("Weather alerts", True)
    
    if st.button("📤 Send Telegram", type="primary"):
        if not chat_id.strip():
            st.error("Please enter a Telegram Chat ID.")
            return
        
        weather = get_weather(city)
        if weather is None:
            st.error(f"City '{city}' not found.")
            return
        
        forecast = get_forecast(city) if include_forecast else []
        alerts = check_bad_weather(city) if include_alerts else []
        rec = get_clothing_recommendation(weather) if include_outfit else None
        
        if not include_weather and not include_forecast and not include_outfit and not include_alerts:
            st.warning("Please select at least one item to send.")
            return
        
        # Build and send Telegram message
        message_text = build_weather_message(weather, forecast, alerts, rec, include_weather)
        result = send_telegram(chat_id, message_text)
        
        if result["success"]:
            if result.get("demo"):
                st.info(f"📝 {result['message']}")
                st.code(result["preview"])
            else:
                st.success(result["message"])
        else:
            st.error(result["message"])


# ==================== Weather Query Page ====================

def show_weather_query():
    """Display weather query page"""
    st.title("🔍 Weather Query")
    
    # Weather query section
    st.subheader("City Weather Query")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        city = st.text_input("Enter city name (English)", st.session_state.current_city, key="weather_city_input")
    with col2:
        st.write("")
        st.write("")
        st.caption("Examples: Beijing, London, Tokyo, New York")
    
    col1, col2 = st.columns(2)
    with col1:
        show_forecast = st.checkbox("Show 5-day forecast", True)
    with col2:
        check_alerts = st.checkbox("Check weather alerts", True)
    
    # Search button
    search_clicked = st.button("🔍 Search Weather", type="primary")
    
    # Store weather data in session state
    if "weather_data" not in st.session_state:
        st.session_state.weather_data = None
    if "forecast_data" not in st.session_state:
        st.session_state.forecast_data = None
    if "alerts_data" not in st.session_state:
        st.session_state.alerts_data = None
    
    if search_clicked:
        # Get current weather
        weather = get_weather(city)
        
        if weather is None:
            st.error(f"❌ City '{city}' not found. Please check the spelling and try again.")
            st.session_state.weather_data = None
            return
        
        st.session_state.weather_data = weather
        st.session_state.forecast_data = get_forecast(city) if show_forecast else []
        st.session_state.alerts_data = check_bad_weather(city) if check_alerts else []
    
    # Display weather data if available
    if st.session_state.weather_data:
        weather = st.session_state.weather_data
        forecast = st.session_state.forecast_data
        alerts = st.session_state.alerts_data
        
        st.subheader(f"Current Weather in {weather['city']}")
        
        # Show metrics
        emoji = get_weather_emoji(weather["main"])
        col1, col2, col3, col4 = st.columns(4)
        col1.metric(f"{emoji} Temperature", f"{weather['temp']}°C")
        col2.metric("Humidity", f"{weather['humidity']}%")
        col3.metric("Wind", f"{weather['wind_speed']} m/s")
        col4.metric("Condition", weather['description'])
        
        # Clothing recommendation
        rec = get_clothing_recommendation(weather)
        st.markdown("---")
        st.markdown(f"👔 **Smart Outfit Suggestion**")
        st.markdown(format_recommendation_html(rec), unsafe_allow_html=True)
        
        # Check for alerts
        if alerts:
            st.error("⚠️ Weather Alerts")
            for alert in alerts:
                st.warning(f"**{alert['type']}**: {alert['message']}")
        
        # Show forecast
        if forecast:
            st.subheader("5-Day Forecast")
            
            cols = st.columns(5)
            for i, day in enumerate(forecast):
                with cols[i]:
                    emoji = get_weather_emoji(day["description"])
                    st.write(f"**{day['weekday']}**")
                    st.write(f"{emoji}")
                    st.write(f"{day['temp_max']}° / {day['temp_min']}°")
                    st.caption(f"👔 {get_forecast_recommendation(day)}")
            
            # Show temperature chart
            chart_data = pd.DataFrame({
                'Day': [f['weekday'] for f in forecast],
                'High': [f['temp_max'] for f in forecast],
                'Low': [f['temp_min'] for f in forecast]
            })
            st.line_chart(chart_data.set_index('Day'))


# ==================== Page Router ====================

if page == "Home":
    show_home()
elif page == "Weather Query":
    show_weather_query()
elif page == "Telegram Push":
    show_telegram_send()

# Footer

st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown(
    "<center>WeatherWiseBot  |  Have a Great Day  🌞</center>",
    unsafe_allow_html=True
)
