"""
WeatherWiseBot - Main Application

"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
# Import weather service and recommendation modules
from weather_service import get_weather, get_forecast, check_bad_weather, get_weather_emoji
from recommendation import get_clothing_recommendation, get_forecast_recommendation, format_recommendation_html
from telegram_service import send_telegram, send_telegram_batch, build_weather_message
from trip_weatherpush_service import send_trip_weather_report
from user_service import (
    register_user, login_user, user_exists,
    get_user, update_user,
    create_group, list_groups, get_group, update_group, delete_group,
    add_group_member, remove_group_member, list_group_members,
    get_group_broadcast_targets,
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
    # Username is always the public identifier. Never fall back to the raw
    # Telegram ID here — legacy rows without a nickname show a safe placeholder
    # and the real Telegram ID stays hidden inside the expander.
    display_name = (user.get("nickname") or "").strip() or "(no username set)"
    # Default: only the username is shown. Telegram ID is hidden inside an
    # expander and only revealed when the user clicks their own name.
    with st.sidebar.expander(f"👤 {display_name}"):
        st.caption("Your Telegram ID:")
        st.code(user["telegram_id"])
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in_user = None
        st.query_params.pop("login_tid", None)
        st.rerun()
else:
    with st.sidebar.expander("🔑 Login / Register"):
        login_id = st.text_input("Telegram ID *", key="login_telegram_id")
        login_nick = st.text_input(
            "Username *",
            key="login_telegram_nick",
            help="Required for new users. This name is shown across the app; "
                 "your Telegram ID stays private.",
        )
        if st.button("Login / Register", key="login_btn", type="primary"):
            tid = login_id.strip()
            nick = login_nick.strip()
            if not tid:
                st.error("Please enter your Telegram ID.")
            elif user_exists(tid):
                # Existing user → straight login, username is already on file.
                user = login_user(tid)
                if user:
                    st.session_state.logged_in_user = user
                    if user.get("favorite_city"):
                        st.session_state.current_city = user["favorite_city"]
                    st.query_params["login_tid"] = user["telegram_id"]
                    st.toast(f"Welcome back, {user.get('nickname') or 'user'}!")
                    st.rerun()
            else:
                # New user → username is required to register.
                if not nick:
                    st.error("New user — please enter a Username to register.")
                else:
                    user = register_user(tid, nick)
                    if user:
                        st.session_state.logged_in_user = user
                        st.query_params["login_tid"] = user["telegram_id"]
                        st.toast(f"Account created. Welcome, {user['nickname']}!")
                        st.rerun()
                    else:
                        st.error("Registration failed. Please try again.")

# Navigation menu with emojis and larger font
st.sidebar.markdown("<br><br>", unsafe_allow_html=True)

if "nav_option" not in st.session_state:
    st.session_state.nav_option = "🏠 Home"

nav_options = ["🏠 Home", "🌦️ Weather Query", "📱 Telegram Push", "🚗 Trip Weather Push", "👤 Account & Groups"]

for option in nav_options:
    if st.sidebar.button(option, use_container_width=True, 
                         type="primary" if st.session_state.nav_option == option else "secondary"):
        st.session_state.nav_option = option
        st.rerun()

page = (
    st.session_state.nav_option
    .replace("🏠 ", "")
    .replace("🌦️ ", "")
    .replace("📱 ", "")
    .replace("🚗 ", "")
    .replace("👥 ", "")
    .replace("👤 ", "")
)

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
        # When logged in, default to "Me" — only the username is shown, the
        # raw Telegram ID stays hidden. The TID input box only appears when the
        # user explicitly switches to "Other" to send to a non-registered chat.
        chat_id = ""
        if st.session_state.logged_in_user:
            current = st.session_state.logged_in_user
            username = current.get("nickname") or "(no username set)"
            send_choice = st.radio(
                "Recipient",
                options=["Me", "Other"],
                horizontal=True,
                key="telegram_recipient",
            )
            if send_choice == "Me":
                chat_id = current["telegram_id"]
                st.info(f"👤 {username}")
            else:
                chat_id = st.text_input("Telegram ID", "", key="telegram_chat_id_other")
        else:
            chat_id = st.text_input("Telegram ID", "", key="telegram_chat_id_anon")

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

    # Auto-fill telegram ID if logged in
    default_trip_id = ""
    if st.session_state.logged_in_user:
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


# ==================== Account & Groups Page ====================

def show_account():
    """Account profile + group management on a single page."""
    st.title("👤 Account & Groups")

    if not st.session_state.logged_in_user:
        st.info("Please login from the sidebar to manage your account and groups.")
        return

    user = st.session_state.logged_in_user
    owner_tid = user["telegram_id"]
    display_name = user.get("nickname") or user["telegram_id"]
    st.success(f"Logged in as: **{display_name}**")

    # ---------- Profile ----------
    st.subheader("👤 Profile Settings")

    current_nickname = user.get("nickname", "")
    nickname = st.text_input(
        "Username (display name)",
        value=current_nickname,
        key="account_nickname",
        help="This name is shown across the app. Your Telegram ID stays private.",
    )

    current_city = user.get("favorite_city", "Hong Kong")
    favorite_city = st.text_input("Preferred City", value=current_city, key="account_city")

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

    # ---------- Groups ----------
    st.markdown("---")
    st.subheader("👥 Groups")
    st.caption("Define a city preference per group, then send weather to all members in one click.")

    st.markdown("##### ➕ Create New Group")
    with st.form("create_group_form"):
        c1, c2 = st.columns(2)
        with c1:
            new_name = st.text_input("Group Name *", key="new_group_name")
        with c2:
            new_city = st.text_input("City Preference", value="Hong Kong", key="new_group_city")
        new_desc = st.text_input("Description (optional)", key="new_group_desc")
        submitted = st.form_submit_button("Create Group", type="primary")
        if submitted:
            if not new_name.strip():
                st.error("Please enter a group name.")
            else:
                gid = create_group(owner_tid, new_name, new_city, new_desc)
                if gid:
                    st.success(f"Group '{new_name.strip()}' created.")
                    st.rerun()
                else:
                    st.error("Failed to create group. Please login again.")

    st.markdown("##### 📋 My Groups")
    groups = list_groups(owner_tid)

    if not groups:
        st.info("No groups yet. Create one above to start batch-pushing weather reports.")
        return

    for g in groups:
        member_label = f"{g['member_count']} member" + ("s" if g['member_count'] != 1 else "")
        header = f"📁 {g['name']}   •   📍 {g['city']}   •   👥 {member_label}"
        with st.expander(header, expanded=False):

            tab_members, tab_broadcast, tab_settings = st.tabs([
                f"👥 Members ({g['member_count']})",
                "📤 Broadcast",
                "⚙️ Settings",
            ])

            # ----- Members tab -----
            with tab_members:
                members = list_group_members(g["id"])
                if members:
                    for m in members:
                        mc1, mc2, mc3 = st.columns([3, 3, 1])
                        mc1.write(m["display_name"] or "_(no name)_")
                        mc2.code(m["telegram_id"])
                        if mc3.button("❌", key=f"rm_{g['id']}_{m['telegram_id']}",
                                      help="Remove member"):
                            remove_group_member(g["id"], m["telegram_id"])
                            st.success(f"Removed {m['telegram_id']}.")
                            st.rerun()
                else:
                    st.caption("No members yet. Add Telegram IDs below.")

                with st.form(f"add_member_form_{g['id']}"):
                    am1, am2 = st.columns(2)
                    new_m_name = am1.text_input(
                        "Display Name (optional)",
                        key=f"add_m_name_{g['id']}",
                    )
                    new_m_tid = am2.text_input(
                        "Telegram ID *",
                        key=f"add_m_tid_{g['id']}",
                    )
                    if st.form_submit_button("➕ Add Member"):
                        if not new_m_tid.strip():
                            st.error("Telegram ID is required.")
                        else:
                            ok = add_group_member(g["id"], new_m_tid, new_m_name)
                            if ok:
                                st.success(f"Added {new_m_tid.strip()} to {g['name']}.")
                                st.rerun()
                            else:
                                st.warning("This Telegram ID is already in the group.")

            # ----- Broadcast tab -----
            with tab_broadcast:
                st.markdown(
                    f"**City:** {g['city']}   |   **Recipients:** {g['member_count']}"
                )
                bc1, bc2, bc3, bc4 = st.columns(4)
                inc_weather = bc1.checkbox("Weather", True, key=f"bw_{g['id']}")
                inc_forecast = bc2.checkbox("Forecast", True, key=f"bf_{g['id']}")
                inc_outfit = bc3.checkbox("Outfit", True, key=f"bo_{g['id']}")
                inc_alerts = bc4.checkbox("Alerts", True, key=f"ba_{g['id']}")

                if st.button("📤 Send Weather to All Members",
                             type="primary",
                             key=f"broadcast_{g['id']}",
                             use_container_width=True):
                    if g["member_count"] == 0:
                        st.error("This group has no members yet.")
                    elif not any([inc_weather, inc_forecast, inc_outfit, inc_alerts]):
                        st.warning("Please select at least one item to send.")
                    else:
                        weather = get_weather(g["city"])
                        if weather is None:
                            st.error(f"City '{g['city']}' not found.")
                        else:
                            forecast = get_forecast(g["city"]) if inc_forecast else []
                            alerts = check_bad_weather(g["city"]) if inc_alerts else []
                            rec = get_clothing_recommendation(weather) if inc_outfit else None
                            message = build_weather_message(
                                weather, forecast, alerts, rec, inc_weather
                            )
                            targets = get_group_broadcast_targets(g["id"])
                            with st.spinner(f"Sending to {len(targets)} recipients..."):
                                result = send_telegram_batch(targets, message)

                            if result.get("demo"):
                                st.info(
                                    f"📝 Demo mode — preview for {result['success']} recipient(s):"
                                )
                                st.code(result.get("preview") or message)
                            else:
                                st.success(
                                    f"✅ Sent to **{result['success']} / {result['total']}** "
                                    f"member(s) of '{g['name']}'."
                                )
                            if result["failed"]:
                                st.error(
                                    f"❌ Failed for {len(result['failed'])} recipient(s):"
                                )
                                for fail in result["failed"]:
                                    st.write(f"- {fail}")

            # ----- Settings tab -----
            with tab_settings:
                with st.form(f"settings_form_{g['id']}"):
                    s1, s2 = st.columns(2)
                    edit_name = s1.text_input("Group Name", value=g["name"], key=f"gn_{g['id']}")
                    edit_city = s2.text_input("City", value=g["city"], key=f"gc_{g['id']}")
                    edit_desc = st.text_input(
                        "Description",
                        value=g.get("description", ""),
                        key=f"gd_{g['id']}",
                    )
                    sc1, sc2 = st.columns(2)
                    save_clicked = sc1.form_submit_button("💾 Save Changes")
                    delete_clicked = sc2.form_submit_button("🗑️ Delete Group")

                    if save_clicked:
                        if not edit_name.strip():
                            st.error("Group name cannot be empty.")
                        else:
                            update_group(
                                g["id"],
                                name=edit_name,
                                city=edit_city,
                                description=edit_desc,
                            )
                            st.success("Group updated.")
                            st.rerun()

                    if delete_clicked:
                        delete_group(g["id"])
                        st.success(f"Group '{g['name']}' deleted.")
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
elif page == "Account & Groups":
    show_account()

# Footer

st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown(
    "<center>WeatherWiseBot  |  Have a Great Day  🌞</center>",
    unsafe_allow_html=True
)
