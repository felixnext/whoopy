"""Streamlit App to Explore Whoop Data

Copyright (c) 2022 Felix Geilert
"""

from datetime import datetime, timedelta
import json
import logging
import math
import os
from pathlib import Path
from typing import Tuple, Dict
import webbrowser

import streamlit as st
from whoopy import WhoopClient, SPORT_IDS

# Page wide Config
st.set_page_config(page_title="Whoop", page_icon="🏃‍♂️")

# define some paths
BASE_DIR = Path(os.path.dirname(__file__))
CONFIG_FILE = BASE_DIR / ".." / ".." / "config.json"
TOKEN_FILE = BASE_DIR / ".tokens" / "whoop_token.json"

# check if files exist
if not os.path.exists(CONFIG_FILE):
    st.error("No config.json found")
    st.stop()

# retrieve modification dates (for caching)
config_mod_date = os.path.getmtime(CONFIG_FILE)


# read the config (make sure this is cached based on last modification date)
@st.cache()
def load_config(config_mod_date):
    # load config and return
    config = json.load(open(CONFIG_FILE, "r"))
    return config


# retrieve the config
config = load_config(config_mod_date)


# Sidebar
st.sidebar.header("Whoop API")
with open(BASE_DIR / "readme.md", "r") as f:
    st.sidebar.markdown(f.read())

# Main
st.title("Whoop API Explorer")

# generate the client
client: WhoopClient = None


# generate the url
@st.cache()
def login_url(config: Dict) -> Tuple[str, str]:
    """Generates the grant url for the whoop api."""
    # retrieve url
    url, state = WhoopClient.auth_url(
        config["client_id"], config["client_secret"], config["redirect_uri"]
    )
    webbrowser.open(url)

    return url, state


# run through login UI
login_container = st.empty()
with login_container.container():

    def login_verify(code: str) -> WhoopClient:
        """Runs through the login flow and returns the client."""
        # generate client
        client = None
        if code:
            try:
                with st.spinner(text="authorizing..."):
                    client = WhoopClient.authorize(
                        code,
                        config["client_id"],
                        config["client_secret"],
                        config["redirect_uri"],
                    )
            except Exception:
                st.error("Code could not be used to generate token")
                client = None
        return client

    # verify that config contains data
    if "client_id" not in config or "client_secret" not in config:
        st.error("No `client_id` or `client_secret` found in config.json")
        st.stop()
    if "redirect_uri" not in config:
        st.error("No `redirect_uri` found in config.json")
        st.stop()

    # verify if config file should be loaded
    if not os.path.exists(TOKEN_FILE):
        # wait for code
        url, state = login_url(config)
        if st.button("Reopen Login"):
            webbrowser.open(url)

        # wait for user to enter the code
        code = st.text_input("Enter Auth Code from Grant url:")
        client = login_verify(code)
    else:
        # try to load from file, otherwise update
        try:
            with st.spinner(text="loading token..."):
                client = WhoopClient.from_token(
                    TOKEN_FILE, config["client_id"], config["client_secret"]
                )
        except Exception as e:
            # provide warning to log
            logging.warning(f"Failed to load token: {e}")
            logging.warning("Delete token and retry")

            # delete token and re-execute login
            os.remove(TOKEN_FILE)

            # wait for code
            url, state = login_url(config)
            if st.button("Reopen Login"):
                webbrowser.open(url)

            # wait for user to enter the code
            code = st.text_input("Enter Auth Code from Grant url:")
            client = login_verify(code)

    # if client setup, store a new token
    if client:
        client.store_token(TOKEN_FILE)

    if not client:
        st.warning("Waiting for client")
        st.stop()

# retrieve client data
user = client.user.profile()
st.success(f"Logged in as {user.first_name} {user.last_name} ({user.user_id})")
login_container.empty()

# display tabs
tab_overview, tab_workout, tab_sleep, tab_raw = st.tabs(
    ["Overview", "Workout", "Sleep", "Raw Data"]
)

# load the latest metrics
baseline_days = 30
# get datetime rounded to 10 min
today = datetime.now().replace(
    second=0, microsecond=0, minute=math.floor(datetime.now().minute / 10) * 10
)


@st.cache()
def load_metrics(baseline_days: int, today: datetime) -> Dict:
    start = today - timedelta(days=baseline_days + 1)
    rec, _ = client.recovery.collection_df(start=start, end=today, get_all_pages=True)
    sleep, _ = client.sleep.collection_df(start=start, end=today, get_all_pages=True)
    cycle, _ = client.cycle.collection_df(start=start, end=today, get_all_pages=True)
    workout, _ = client.workout.collection_df(
        start=start, end=today, get_all_pages=True
    )

    return rec, sleep, cycle, workout


with st.spinner(text="loading metrics..."):
    rec, sleep, cycle, workout = load_metrics(baseline_days, today)
    sleep_nonap = sleep[sleep["nap"] == False]


with tab_overview:
    # display metrics
    st.header("Current Metrics")
    st.text(f"Compared to {baseline_days} day baseline")

    # define items
    items = [
        {"label": "Recovery", "series": rec["score.recovery_score"]},
        {"label": "Resting HR", "series": rec["score.resting_heart_rate"]},
        {"label": "HRV", "series": rec["score.hrv_rmssd_milli"], "unit": "rmssd"},
        {"label": "SPO²", "series": rec["score.spo2_percentage"], "unit": "%"},
        {"label": "Skin Temp", "series": rec["score.skin_temp_celsius"], "unit": "°C"},
        {
            "label": "Resp Rate",
            "series": sleep_nonap["score.respiratory_rate"],
            "unit": "rpm",
        },
    ]

    # iterate rows
    max_items = 3
    rows = math.ceil(len(items) / max_items)
    for row in range(rows):
        pos = row * max_items
        cols = st.columns(max_items)
        for i, item in enumerate(items[pos : pos + max_items]):
            val = item["series"].iloc[0]
            baseline = item["series"].iloc[1:].mean()
            unit = item.get("unit", "")
            cols[i].metric(
                label=item["label"],
                value=f"{val:.2f} {unit}",
                delta=f"{val - baseline:.2f} {unit}",
            )

with tab_workout:
    # display workout metrics
    st.header("Workouts per Day")
    workout_gp = workout.copy()
    workout_gp["date"] = workout_gp["start"].dt.date
    workout_grouped = workout_gp.groupby("date")["id"].count()
    st.bar_chart(workout_grouped)

    # display id distribution
    st.header("Workout Type Distribution")
    workout_gp = workout.copy()
    workout_gp["sport"] = workout_gp["sport_id"].map(SPORT_IDS)
    workout_grouped = workout_gp.groupby("sport")["id"].count()
    st.bar_chart(workout_grouped)


with tab_sleep:
    sleep_nonap_gp = sleep_nonap.copy()
    sleep_nonap_gp["date"] = sleep_nonap_gp["end"].dt.date
    sleep_group = sleep_nonap_gp.groupby("date")[
        "score.sleep_efficiency_percentage"
    ].mean()

    # display
    st.header("Sleep Efficiency")
    st.bar_chart(sleep_group)

with tab_raw:
    raw_data = {
        "recovery": rec,
        "sleep": sleep,
        "cycle": cycle,
        "workout": workout,
    }

    # display raw data
    select = st.selectbox("Select Data", list(raw_data.keys()))

    # display data
    st.dataframe(raw_data[select])

    # allow download
    st.download_button(
        label="Download as CSV",
        data=raw_data[select].to_csv().encode("utf-8"),
        file_name=f"{select}.csv",
        mime="text/csv",
    )
    st.download_button(
        label="Download as JSON",
        data=raw_data[select].to_json().encode("utf-8"),
        file_name=f"{select}.json",
        mime="application/json",
    )
