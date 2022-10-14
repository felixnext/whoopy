"""Main Client for retrieving Whoop data

This contains information for the unofficial version 7 of the Whoop API.

Copyright (C) 2022 Felix Geilert
"""
import json
from typing import Dict, Union

import requests
import configparser
import logging
from datetime import datetime

from dateutil import parser
import pandas as pd
import numpy as np
from time_helper import create_intervals, localize_datetime


# define default whoop date format
DATE_FORMAT = "%Y-%m-%d"

# define API specifications
API_VERSION = "7"
API_URL = f"https://api-{API_VERSION}.whoop.com"

# columns that should be converted
STR_COLS = ["strain.workouts"]


class AuthenticationError(Exception):
    pass


def whoop_time_str(dt: Union[datetime, str]):
    """Converts a datetime object into a whoop timestring"""
    # convert to utc
    dt_utc = localize_datetime(dt, "Etc/UTC")
    ms = int(str(dt_utc.microsecond)[0:3])
    return f"{dt_utc.strftime(DATE_FORMAT)}T{dt_utc.strftime('%H:%M:%S')}.{ms:03}Z"


class WhoopClient:
    """
    A class object to allow a user to login and store their authorization code,
    then perform pulls using the code in order to access different types of data

    Args:
        auth_code (str): Authorization Code for whoop login
        whoop_id (str): Username
    """

    def __init__(
        self,
        auth_token=None,
        whoop_id=None,
        refresh_token=None,
        current_datetime=datetime.utcnow(),
    ):
        # create some general params
        self.auth_token = auth_token
        self.refresh_token = refresh_token
        self.whoop_id = whoop_id
        self.current_datetime = current_datetime
        self.start_datetime = None
        self.all_activities = None
        self.sport_dict = None
        self.all_sleep_events = None

        # check if whoop id should be pulled
        if self.auth_token and not self.start_datetime:
            self.pull_userinfo()

    def _create_url(self, postfix="", auth=False, user=True):
        """Generates the URL of the whoop endpoints"""
        base_url = API_URL

        # check for auth
        if auth:
            return f"{base_url}/oauth/token"

        # check for user
        if user:
            if not self.whoop_id:
                raise ValueError("No whoop user has been authenticated!")
            base_url = f"{API_URL}/users/{self.whoop_id}"

        # generate url
        return f"{base_url}/{postfix}"

    def pull_api(self, url, params=None, df=False):
        """Generalized function to retrieve data from the API.

        Args:
            url: Path that should be pulled
            params: Query Parameters to be passed
            df: Defines if the output data should be parsed as dataframe
        """
        # provides the authorization code for the header (if provided)
        headers = {}
        if self.auth_token:
            headers["authorization"] = f"Bearer {self.auth_token}"

        # send the request
        pull = requests.get(url, params=params, headers=headers)

        # retrieve json data from the API
        if pull.status_code == 200 and len(pull.content) > 1:
            if df:
                d = pd.json_normalize(pull.json())

                # convert potential str columns
                for col in STR_COLS:
                    # make sure column exists
                    if col not in d.columns:
                        continue

                    # check for type
                    if d[col].dtype == "object":
                        d[col] = d[col].apply(
                            lambda x: json.loads(
                                str(x).replace("'", '"').replace('u"', '"')
                            )
                        )

                return d
            else:
                return pull.json()
        elif pull.status_code == 401 and self.auth_refresh < 3:
            raise AuthenticationError("Unable to authenticate wiht backend")
        else:
            raise IOError(
                f"Unable to retrieve API response for url ({url}): {pull.status_code}",
                pull,
                params,
            )

    def _parse_authentication(self, body):
        """Parses the authentication response"""
        self.whoop_id = body["user"]["id"]
        self.auth_token = body["access_token"]
        self.refresh_token = body.get("refresh_token")
        start_time = body["user"]["profile"]["createdAt"]
        self.start_datetime = parser.isoparse(start_time)
        logging.info("Authentication successful")

        return self.get_auth()

    def authenticate_ini(self, ini_file):
        # read the user data provided in ini
        config = configparser.ConfigParser()
        config.read(ini_file)
        username = config["whoop"]["username"]
        password = config["whoop"]["password"]

        # pass along
        return self.authenticate_user(username, password)

    def authenticate_user(self, username, password):
        # create header for token request
        headers = {
            "username": username,
            "password": password,
            "grant_type": "password",
            "issueRefresh": False,
        }

        # send request
        auth = requests.post(self._create_url(auth=True), json=headers)

        # check for errors
        if auth.status_code != 200:
            raise AuthenticationError(f"Unable to complete authentication: {auth.text}")

        # parse the data
        return self._parse_authentication(auth.json())

    def authenticate_refresh(self, refresh_token=None):
        # retrieve token
        refresh_token = refresh_token if refresh_token else self.refresh_token

        # check if token is set
        if not refresh_token:
            raise ValueError("No Refresh Token provided")

        headers = {
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "issueRefresh": True,
        }

        # send request
        auth = self.pull_api(self._create_url(auth=True), params=headers)

        # check for errors
        if auth.status_code != 200:
            raise AuthenticationError(f"Unable to complete authentication: {auth.text}")

        # parse the data
        return self._parse_authentication(auth.json())

    def authenticate_code(self, auth_code):
        raise NotImplementedError("Public APIs currently unsupported by whoop")

    def get_auth(self):
        """Returns current authentication data"""
        return (
            self.auth_token,
            self.refresh_token,
            {"user_id": self.whoop_id, "createdAt": self.start_datetime},
        )

    def pull_userinfo(self):
        """Retrieves user information based on the whoop_id"""
        data = self.pull_api(self._create_url())
        start_time = data["createdAt"]
        self.start_datetime = parser.isoparse(start_time)
        return data

    def pull_sleep_main(self, sleep_id):
        sleep = self.pull_api(self._create_url(f"sleeps/{sleep_id}"))

        # retrieve the data
        main_df = pd.json_normalize(sleep)
        return main_df

    def pull_sleep_events(self, sleep_id):
        sleep = self.pull_api(self._create_url(f"sleeps/{sleep_id}"))

        # retrieve the data
        events_df = pd.json_normalize(sleep["events"])
        events_df["id"] = sleep_id
        return events_df

    def get_keydata_raw(self, start=None, end=None):
        """Retrieves all data as array of raw jsons from the creation time of the user."""
        # store all results
        results = []

        # starts crawling from user creation-time
        if self.start_datetime:
            # parse the data
            if start is not None:
                if isinstance(start, str):
                    start_date = parser.parse(start)
                elif isinstance(start, datetime):
                    start_date = start
                else:
                    raise ValueError(
                        f"Start argument ({start}) is not a valid datetime ({type(start)})"
                    )
                start_date = start_date.replace(tzinfo=None, hour=0, minute=0, second=0)
            # otherwise use default data
            else:
                start_date = self.start_datetime.replace(tzinfo=None)
            if end is not None:
                if isinstance(end, str):
                    end_date = parser.parse(end)
                elif isinstance(end, datetime):
                    end_date = end
                else:
                    raise ValueError(
                        f"End argument ({end}) is not a valid datetime ({type(end)})"
                    )
                end_date = end_date.replace(tzinfo=None)
            else:
                end_date = datetime.utcnow()

            # generate range
            date_range = create_intervals(
                start_date, end_date, interval=7, round_days=True
            )

            # retrieve data accordingly
            for dates in date_range:
                cycle_params = {
                    "start": whoop_time_str(dates[0]),
                    "end": whoop_time_str(dates[1]),
                }
                json_data = self.pull_api(
                    self._create_url("cycles"), params=cycle_params
                )

                results.append(json_data)
        else:
            raise RuntimeError("Please run the authorization function first")

        # return all data
        return results

    def get_keydata(self, raw_data=None, start=None, end=None):
        """
        This function returns a dataframe of WHOOP metrics for each day of WHOOP membership.
        In the resulting dataframe, each day is a row and contains strain, recovery, and sleep information
        """
        # retrieve all raw data and convert to dataframes
        if raw_data is None:
            raw_data = self.get_keydata_raw(start, end)
        df_data = [pd.json_normalize(data) for data in raw_data]
        all_data = pd.concat(df_data)

        # check length
        if len(all_data) == 0:
            return None

        # update the dataframe
        all_data.reset_index(drop=True, inplace=True)

        # fixing the day column so it's not a list
        all_data["days"] = all_data["days"].map(lambda d: d[0])
        all_data.rename(columns={"days": r"day"}, inplace=True)

        # Putting all time into minutes instead of milliseconds
        sleep_cols = [
            "qualityDuration",
            "needBreakdown.baseline",
            "needBreakdown.debt",
            "needBreakdown.naps",
            "needBreakdown.strain",
            "needBreakdown.total",
        ]
        for sleep_col in sleep_cols:
            if sleep_col in all_data.columns:
                all_data["sleep." + sleep_col] = (
                    all_data["sleep." + sleep_col]
                    .astype(float)
                    .apply(lambda x: np.nan if np.isnan(x) else x / 60000)
                )
            else:
                all_data["sleep." + sleep_col] = np.nan

        # Making nap variable
        all_data["nap_duration"] = all_data["sleep.naps"].apply(
            lambda x: x[0]["qualityDuration"] / 60000
            if len(x) == 1
            else (
                sum(
                    [
                        y["qualityDuration"]
                        for y in x
                        if y["qualityDuration"] is not None
                    ]
                )
                / 60000
                if len(x) > 1
                else 0
            )
        )
        all_data.drop(["sleep.naps"], axis=1, inplace=True)

        # dropping duplicates subsetting because of list columns
        all_data.drop_duplicates(subset=["day", "sleep.id"], inplace=True)

        return all_data

    def get_sports(self):
        """Retrieve a list of all sports"""
        sports = self.pull_api(self._create_url("sports", user=False))
        sport_dict = {sport["id"]: sport["name"] for sport in sports}
        self.sport_dict = self.sport_dict
        return sport_dict

    def _apply_zone(self, item: Dict[str, float], zone: int):
        if item is None or zone not in item:
            return None
        return item[zone] / 60000.0

    def get_activities(
        self, all_data=None, update_sport_dict=False, start=None, end=None
    ):
        """
        Activity data is pulled through the get_keydata functions so if the data pull is present, this function
        just transforms the activity column into a dataframe of activities, where each activity is a row.
        If it has not been pulled, this function runs the key data function then returns the activity dataframe
        """
        # pull data from all activities that have been logged so far
        if self.sport_dict and update_sport_dict is False:
            sport_dict = self.sport_dict
        else:
            sport_dict = self.get_sports()

        # make sure user is logged in
        if self.start_datetime:
            # check if existing data is used
            if all_data is not None:
                data = all_data
            else:
                data = self.get_keydata(start=start, end=end)

            # ensure data has the right format
            if data["strain.workouts"].dtype == "object":
                data["strain.workouts"] = data["strain.workouts"].apply(
                    lambda x: eval(str(x))
                )

            # retrieve the data
            data = data[data["strain.workouts"].apply(len) > 0]
            data = data.explode("strain.workouts")
            # data["strain.workouts"] = pd.json_normalize(data["strain.workouts"])
            # act_data = data["strain.workouts"].apply(pd.Series)
            act_data = pd.json_normalize(data["strain.workouts"])
            # act_data["day"] = data["day"]

            # check if there is data
            if len(data) == 0:
                return None

            # update the data
            act_data[["during.upper", "during.lower"]] = act_data[
                ["during.upper", "during.lower"]
            ].apply(pd.to_datetime)
            act_data["total_minutes"] = act_data.apply(
                lambda x: (x["during.upper"] - x["during.lower"]).total_seconds()
                / 60.0,
                axis=1,
            )
            for z in range(0, 6):
                act_data["zone{}_minutes".format(z + 1)] = act_data["zones"].apply(
                    lambda x: self._apply_zone(x, z)
                )
            act_data["sport_name"] = act_data.sportId.apply(lambda x: sport_dict[x])

            act_data["day"] = act_data["during.lower"].dt.strftime(DATE_FORMAT)
            act_data.drop(["zones", "during.bounds"], axis=1, inplace=True)
            act_data.drop_duplicates(inplace=True)
            self.all_activities = act_data
            return act_data
        else:
            raise RuntimeError("Please run the authorization function first")

    def get_sleep(self, all_data=None, start=None, end=None):
        """
        This function returns all sleep metrics in a data frame, for the duration of user's WHOOP membership.
        Each row in the data frame represents one night of sleep
        """
        if self.auth_token:
            # check if previous data can be used
            if all_data is not None:
                data = all_data
            else:
                data = self.get_keydata(start=None, end=None)

            # getting all the sleep ids
            sleep_ids = data["sleep.id"].values.tolist()
            sleep_list = [int(x) for x in sleep_ids if pd.isna(x) is False]
            all_sleep = pd.DataFrame()
            for s in sleep_list:
                m = self.pull_sleep_main(s)
                all_sleep = pd.concat([all_sleep, m])

            if len(all_sleep) == 0:
                return None

            # Cleaning sleep data
            sleep_update = [
                "qualityDuration",
                "latency",
                "debtPre",
                "debtPost",
                "needFromStrain",
                "sleepNeed",
                "habitualSleepNeed",
                "timeInBed",
                "lightSleepDuration",
                "slowWaveSleepDuration",
                "remSleepDuration",
                "wakeDuration",
                "arousalTime",
                "noDataDuration",
                "creditFromNaps",
                "projectedSleep",
            ]

            for col in sleep_update:
                if col in all_sleep.columns:
                    all_sleep[col] = (
                        all_sleep[col]
                        .astype(float)
                        .apply(lambda x: np.nan if np.isnan(x) else x / 60000)
                    )
                else:
                    all_data[col] = np.nan

            for col in ["during.bounds", "events"]:
                if col in all_sleep:
                    all_sleep.drop([col], axis=1, inplace=True)
            return all_sleep
        else:
            raise RuntimeError("Please run the authorization function first")

    def get_sleep_events_all(self, all_data=None, all_sleep=None, start=None, end=None):
        """
        This function returns all sleep events in a data frame, for the duration of user's WHOOP membership.
        Each row in the data frame represents an individual sleep event within an individual night of sleep.
        Sleep events can be joined against the sleep or main datasets by sleep id.
        All sleep times are returned in minutes.
        """
        if self.auth_token:
            # check for previous data
            if all_data is not None:
                data = all_data
            else:
                data = self.get_keydata(start=None, end=None)

            # getting all the sleep ids
            if all_sleep is not None:
                sleep_events = all_sleep[["activityId", "events"]]
                all_sleep_events = pd.concat(
                    [
                        pd.concat(
                            [
                                pd.json_normalize(events),
                                pd.DataFrame({"id": len(events) * [sleep]}),
                            ],
                            axis=1,
                        )
                        for events, sleep in zip(
                            sleep_events["events"], sleep_events["activityId"]
                        )
                    ]
                )
            else:
                sleep_ids = data["sleep.id"].values.tolist()
                sleep_list = [int(x) for x in sleep_ids if pd.isna(x) == False]
                all_sleep_events = pd.DataFrame()
                for s in sleep_list:
                    events = self.pull_sleep_events(s)
                    all_sleep_events = pd.concat([all_sleep_events, events])

            # Cleaning sleep events data
            all_sleep_events["during.lower"] = pd.to_datetime(
                all_sleep_events["during.lower"]
            )
            all_sleep_events["during.upper"] = pd.to_datetime(
                all_sleep_events["during.upper"]
            )
            all_sleep_events.drop(["during.bounds"], axis=1, inplace=True)
            all_sleep_events["total_minutes"] = all_sleep_events.apply(
                lambda x: (x["during.upper"] - x["during.lower"]).total_seconds()
                / 60.0,
                axis=1,
            )

            return all_sleep_events
        else:
            raise RuntimeError("Please run the authorization function first")

    def get_hr(self, df=False, start=None, end=None):
        """
        This function will pull every heart rate measurement recorded for the life of WHOOP membership.
        The default return for this function is a list of lists, where each "row" contains the date, time, and hr value.
        The measurements are spaced out every ~6 seconds on average.

        To return a dataframe, set df=True. This will take a bit longer, but will return a data frame.

        NOTE: This api pull takes about 6 seconds per week of data ... or 1 minutes for 10 weeks of data,
        so be careful when you pull, it may take a while.
        """
        if self.start_datetime:
            # generate date range
            date_range = create_intervals(start, end, interval=6, round_days=True)

            # create request for date range
            hr_list = []
            for dates in date_range:
                params = {
                    "start": whoop_time_str(dates[0]),
                    "end": whoop_time_str(dates[1]),
                    "order": "t",
                    "step": 6,
                }
                try:
                    hr_vals = self.pull_api(
                        self._create_url("metrics/heart_rate"), params=params
                    )["values"]
                except IOError:
                    print(f"Unable to pull data from {dates[0]} to {dates[1]}")
                    logging.warning(
                        f"Unable to pull data from {dates[0]} to {dates[1]}"
                    )
                    continue
                hr_values = [
                    [
                        datetime.utcfromtimestamp(h["time"] / 1e3).date(),
                        datetime.utcfromtimestamp(h["time"] / 1e3).time(),
                        h["data"],
                    ]
                    for h in hr_vals
                ]
                hr_list.extend(hr_values)

            # check length
            if len(hr_list) == 0:
                return None

            # check conversion
            if df:
                hr_df = pd.DataFrame(hr_list)
                hr_df.columns = ["date", "time", "hr"]
                hr_df = hr_df.reset_index()[["date", "time", "hr"]]
                return hr_df
            else:
                return hr_list
        else:
            raise RuntimeError("Please run the authorization function first")
