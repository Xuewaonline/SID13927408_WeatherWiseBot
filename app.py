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
from trip_weatherpush_service import send_trip_weather_report
from user_service import (
    register_or_login, get_user, update_user,
    add_saved_account, get_saved_accounts, update_saved_account, delete_saved_account,
)

# ==================== Page Setup ====================

st.set_page_config(
    page_title="WeatherWiseBot",
    page_icon="🌤️",
    layout="wide"
)

# Initialize session state
if "current_city" not in st.session_state:
    st.session_state.current_city = "Hong Kong"

if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = None

# Auto-login from query params (survives page refresh)
if st.session_state.logged_in_user is None:
    saved_tid = st.query_params.get("login_tid")
    if saved_tid:
        user = get_user(saved_tid)
        if user:
            st.session_state.logged_in_user = user
            if user.get("favorite_city"):
                st.session_state.current_city = user["favorite_city"]

# ==================== Sidebar ====================

st.sidebar.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
st.sidebar.markdown("<h1 style='text-align: center; margin: 0; font-size: 1.8rem;'>🌤️<br>WeatherWiseBot</h1>", unsafe_allow_html=True)

# Login section in sidebar
st.sidebar.markdown("<br>", unsafe_allow_html=True)
st.sidebar.markdown("**👤 Account**")

if st.session_state.logged_in_user:
    user = st.session_state.logged_in_user
    display_name = user.get("nickname") or user["telegram_id"]
    st.sidebar.success(f"👋 {display_name}")
    if st.sidebar.button("🚪 Logout"):
        st.session_state.logged_in_user = None
        st.session_state.pop("active_account", None)
        st.query_params.pop("login_tid", None)
        st.rerun()
else:
    with st.sidebar.expander("Login with Telegram ID"):
        login_id = st.text_input("Telegram ID", key="login_telegram_id")
        if st.button("Login", key="login_btn"):
            if login_id.strip():
                user = register_or_login(login_id)
                if user:
                    st.session_state.logged_in_user = user
                    if user.get("favorite_city"):
                        st.session_state.current_city = user["favorite_city"]
                    st.query_params["login_tid"] = user["telegram_id"]
                    st.rerun()
            else:
                st.error("Please enter your Telegram ID")

# Navigation menu with emojis and larger font
st.sidebar.markdown("<br><br>", unsafe_allow_html=True)

if "nav_option" not in st.session_state:
    st.session_state.nav_option = "🏠 Home"

nav_options = ["🏠 Home", "🌦️ Weather Query", "📱 Telegram Push", "🚗 Trip Weather Push", "👤 Account"]

for option in nav_options:
    if st.sidebar.button(option, use_container_width=True, 
                         type="primary" if st.session_state.nav_option == option else "secondary"):
        st.session_state.nav_option = option
        st.rerun()

page = st.session_state.nav_option.replace("🏠 ", "").replace("🌦️ ", "").replace("📱 ", "").replace("🚗 ", "").replace("👤 ", "")

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

    # Auto-fill telegram ID and city from switched sub-account
    default_chat_id = ""
    if st.session_state.get("active_account"):
        default_chat_id = st.session_state.active_account["tid"]
    elif st.session_state.logged_in_user:
        default_chat_id = st.session_state.logged_in_user["telegram_id"]

    col1, col2 = st.columns(2)
    with col1:
        city = st.text_input("City name", st.session_state.current_city, key="telegram_city")
    with col2:
        chat_id = st.text_input("Telegram ID", default_chat_id, key="telegram_chat_id")
    
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
            st.error("Please enter a Telegram ID.")
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


# ==================== Trip Weather Push Page ====================

def show_trip_weather():
    st.title("🚗 Trip Weather Push")

    # ---------- Instant Push ----------
    st.subheader("Instant Trip Weather Report")

    col1, col2 = st.columns(2)
    with col1:
        departure_city = st.text_input("Departure City", "", key="trip_dep_city")
        departure_time = st.datetime_input(
            "Departure Time",
            value=datetime.now(),
            key="trip_dep_time"
        )
    with col2:
        arrival_city = st.text_input("Arrival City", "", key="trip_arr_city")
        arrival_time = st.datetime_input(
            "Arrival Time",
            value=datetime.now() + timedelta(hours=2),
            key="trip_arr_time"
        )

    # Auto-fill telegram ID from switched sub-account
    default_trip_id = ""
    if st.session_state.get("active_account"):
        default_trip_id = st.session_state.active_account["tid"]
    elif st.session_state.logged_in_user:
        default_trip_id = st.session_state.logged_in_user["telegram_id"]

    trip_chat_id = st.text_input("Telegram ID", default_trip_id, key="trip_chat_id")

    if st.button("📤 Send Weather Report", type="primary"):
        if not trip_chat_id.strip():
            st.error("Please enter a Telegram ID.")
            return
        if not departure_city.strip() or not arrival_city.strip():
            st.error("Please enter both departure and arrival cities.")
            return

        result = send_trip_weather_report(
            trip_chat_id, departure_city, departure_time, arrival_city, arrival_time
        )

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


# ==================== Account Page ====================

def show_account():
    """Display user account and preferences page."""
    st.title("👤 My Account")

    if not st.session_state.logged_in_user:
        st.info("Please login from the sidebar to manage your account.")
        return

    user = st.session_state.logged_in_user
    st.success(f"Logged in as: **{user['telegram_id']}**")

    # ---------- Profile Settings ----------
    st.subheader("Profile Settings")

    current_nickname = user.get("nickname", "")
    nickname = st.text_input("Nickname", value=current_nickname, key="account_nickname")

    current_city = user.get("favorite_city", "Hong Kong")
    favorite_city = st.text_input("My Preferred City", value=current_city, key="account_city")

    if st.button("💾 Save Profile", type="primary"):
        update_user(
            user["telegram_id"],
            nickname=nickname.strip(),
            favorite_city=favorite_city.strip(),
        )
        updated = get_user(user["telegram_id"])
        st.session_state.logged_in_user = updated
        if favorite_city.strip():
            st.session_state.current_city = favorite_city.strip()
        st.success("Profile saved!")
        st.rerun()

    st.markdown("---")

    # ---------- Saved Accounts (常用账户) ----------
    st.subheader("📒 Saved Accounts")
    st.caption("Add frequently used Telegram accounts with their preferred cities. "
               "They will be available for quick selection across the app.")

    saved = get_saved_accounts(user["telegram_id"])

    # Display existing saved accounts
    if saved:
        for acct in saved:
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 3, 2, 1])
                with col1:
                    st.write(f"**{acct['account_name']}**")
                with col2:
                    st.write(f"ID: `{acct['account_telegram_id']}`")
                with col3:
                    st.write(f"City: {acct['preferred_city']}")
                with col4:
                    if st.button("🗑️", key=f"del_acct_{acct['id']}"):
                        delete_saved_account(acct["id"])
                        st.success(f"Deleted '{acct['account_name']}'")
                        st.rerun()

        st.markdown("---")

    # Add new saved account form
    with st.expander("➕ Add New Account"):
        a_name = st.text_input("Account Name *", placeholder="e.g. Alice, Bob", key="new_acct_name")
        a_tid = st.text_input("Telegram ID *", placeholder="e.g. 123456789", key="new_acct_tid")
        a_city = st.text_input("Preferred City", value="Hong Kong", key="new_acct_city")

        if st.button("Add Account", key="add_acct_btn"):
            ok, msg = add_saved_account(
                user["telegram_id"], a_name, a_tid, a_city,
            )
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    st.markdown("---")

    # ---------- Quick switch to a saved account ----------
    if saved:
        st.subheader("🔄 Switch to Saved Account")
        st.caption("Switch to a saved account. Both preferred city and Telegram ID will update across all pages.")

        # Show current active sub-account
        active_acct = st.session_state.get("active_account")
        if active_acct:
            st.info(f"Active: **{active_acct['name']}** — City: {active_acct['city']} — Telegram: `{active_acct['tid']}`")
            if st.button("↩️ Back to My Account", key="reset_acct_btn"):
                st.session_state.current_city = user.get("favorite_city") or "Hong Kong"
                st.session_state.pop("active_account", None)
                st.rerun()

        acct_labels = [f"{a['account_name']} — {a['preferred_city']} — ID: {a['account_telegram_id']}" for a in saved]
        selected_idx = st.selectbox("Select an account", range(len(acct_labels)),
                                    format_func=lambda i: acct_labels[i],
                                    key="quick_switch_select")

        if st.button("🔄 Switch Account", type="primary", key="switch_acct_btn"):
            chosen = saved[selected_idx]
            st.session_state.current_city = chosen["preferred_city"]
            st.session_state.active_account = {
                "name": chosen["account_name"],
                "tid": chosen["account_telegram_id"],
                "city": chosen["preferred_city"],
            }
            st.success(f"Switched to **{chosen['account_name']}** — City: {chosen['preferred_city']}, Telegram: `{chosen['account_telegram_id']}`")
            st.rerun()


# ==================== Page Router ====================

if page == "Home":
    show_home()
elif page == "Weather Query":
    show_weather_query()
elif page == "Telegram Push":
    show_telegram_send()
elif page == "Trip Weather Push":
    show_trip_weather()
elif page == "Account":
    show_account()

# Footer

st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown(
    "<center>WeatherWiseBot  |  Have a Great Day  🌞</center>",
    unsafe_allow_html=True
)
