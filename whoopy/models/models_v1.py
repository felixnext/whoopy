"""Holds data models for the whoop api.

Copyright (c) 2022 Felix Geilert
"""

from abc import abstractmethod
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Union
from pydantic import BaseModel
import time_helper as th


class UserProfile(BaseModel):
    """Represents a user profile."""

    user_id: int
    email: str
    first_name: str
    last_name: str


class UserMeasurements(BaseModel):
    """Stores user measurements."""

    height_meter: float
    weight_kilogram: float
    max_heart_rate: int


class UserData(BaseModel):
    """Base Data that is used for most user data objects"""

    user_id: int
    created_at: datetime
    updated_at: datetime
    timezone_offset: Optional[str] = None
    score_state: str

    @classmethod
    @abstractmethod
    def _dict_parse(cls, data: Dict) -> Dict[str, Any]:
        return data

    @classmethod
    def from_dict(cls, data: Dict, correct_offset: bool = False):
        # generate timedelta from timezone offset
        td = timedelta(days=0)
        if correct_offset and "timezone_offset" in data:
            to_str = data["timezone_offset"]

            # check if negative
            negative = to_str[0] == "-"
            if to_str[0] in ["+", "-"]:
                to_str = to_str[1:]

            # parse hours and minutes to int
            hours, minutes = to_str.split(":")
            hours = int(hours)
            minutes = int(minutes)

            # generate timedelta
            td = timedelta(hours=hours, minutes=minutes)
            if negative:
                td *= -1

        # update the datetimes
        for dt in ["created_at", "updated_at", "start", "end"]:
            if dt in data and data[dt] is not None:
                date = datetime.strptime(data[dt], "%Y-%m-%dT%H:%M:%S.%fZ")
                data[dt] = th.any_to_datetime(date) + td
        data = cls._dict_parse(data)

        return cls(**data)


class UserCycleScore(BaseModel):
    strain: float
    kilojoule: float
    average_heart_rate: int
    max_heart_rate: int

    @property
    def calories(self):
        return self.kilojoule / 4.184


class UserCycle(UserData):
    """Stores data of the user cycle."""

    id: int
    start: datetime
    end: Optional[datetime] = None
    score: Optional[UserCycleScore] = None

    @classmethod
    def _dict_parse(cls, data: Dict) -> Dict[str, Union[Any, UserCycleScore]]:
        if "score" in data and data["score"] is not None:
            data["score"] = UserCycleScore(**data["score"])

        return data


class UserSleepStages(BaseModel):
    """Stores the sleep stages."""

    total_in_bed_time_milli: int
    total_awake_time_milli: int
    total_no_data_time_milli: int
    total_light_sleep_time_milli: int
    total_slow_wave_sleep_time_milli: int
    total_rem_sleep_time_milli: int
    sleep_cycle_count: int
    disturbance_count: int


class UserSleepNeed(BaseModel):
    """Stores the sleep need."""

    baseline_milli: int
    need_from_sleep_debt_milli: int
    need_from_recent_strain_milli: int
    need_from_recent_nap_milli: int


class UserSleepScore(BaseModel):
    """Stores the score of the user sleep."""

    stage_summary: Optional[UserSleepStages] = None
    sleep_needed: Optional[UserSleepNeed] = None
    respiratory_rate: Optional[float] = None
    sleep_performance_percentage: Optional[float] = None
    sleep_consistency_percentage: Optional[float] = None
    sleep_efficiency_percentage: Optional[float] = None


class UserSleep(UserData):
    """Stores data for user sleep."""

    id: int
    nap: bool
    start: datetime
    end: Optional[datetime] = None
    score: Optional[UserSleepScore] = None

    @classmethod
    def _dict_parse(cls, data: Dict):
        if "score" in data and data["score"] is not None:
            score_dict = data["score"]
            if (
                "stage_summary" in score_dict
                and score_dict["stage_summary"] is not None
            ):
                score_dict["stage_summary"] = UserSleepStages(
                    **score_dict["stage_summary"]
                )
            else:
                score_dict["stage_summary"] = None
            if "sleep_needed" in score_dict and score_dict["sleep_needed"] is not None:
                score_dict["sleep_needed"] = UserSleepNeed(**score_dict["sleep_needed"])
            else:
                score_dict["sleep_needed"] = None
            data["score"] = UserSleepScore(**score_dict)

        return data


class UserRecoveryScore(BaseModel):
    """Score of users recovery."""

    user_calibrating: bool
    recovery_score: float
    resting_heart_rate: float
    hrv_rmssd_milli: float
    spo2_percentage: Optional[float] = None
    skin_temp_celsius: Optional[float] = None


class UserRecovery(UserData):
    """Stores data for user recovery."""

    cycle_id: int
    sleep_id: int
    score: UserRecoveryScore

    @classmethod
    def _dict_parse(cls, data: Dict) -> Dict[str, Union[Any, UserRecoveryScore]]:
        if "score" in data and data["score"] is not None:
            data["score"] = UserRecoveryScore(**data["score"])

        return data


class UserWorkoutZoneDuration(BaseModel):
    """Stores the duration of the workout zone."""

    zone_zero_milli: int
    zone_one_milli: int
    zone_two_milli: int
    zone_three_milli: int
    zone_four_milli: int
    zone_five_milli: int


class UserWorkoutScore(BaseModel):
    """Score of the user workout."""

    strain: float
    average_heart_rate: int
    max_heart_rate: int
    kilojoule: float
    percent_recorded: float
    distance_meter: Optional[float] = None
    altitude_gain_meter: Optional[float] = None
    altitude_change_meter: Optional[float] = None
    zone_duration: Optional[UserWorkoutZoneDuration] = None


class UserWorkout(UserData):
    """Stores information about a user workout"""

    id: int
    start: datetime
    end: Optional[datetime] = None
    sport_id: int
    score: Optional[UserWorkoutScore] = None

    @classmethod
    def _dict_parse(cls, data: Dict):
        if "score" in data and data["score"] is not None:
            score_dict = data["score"]
            if (
                "zone_duration" in score_dict
                and score_dict["zone_duration"] is not None
            ):
                score_dict["zone_duration"] = UserWorkoutZoneDuration(
                    **score_dict["zone_duration"]
                )
            data["score"] = UserWorkoutScore(**score_dict)

        return data


SPORT_IDS = {
    -1: "Activity",
    0: "Running",
    1: "Cycling",
    16: "Baseball",
    17: "Basketball",
    18: "Rowing",
    19: "Fencing",
    20: "Field Hockey",
    21: "Football",
    22: "Golf",
    24: "Ice Hockey",
    25: "Lacrosse",
    27: "Rugby",
    28: "Sailing",
    29: "Skiing",
    30: "Soccer",
    31: "Softball",
    32: "Squash",
    33: "Swimming",
    34: "Tennis",
    35: "Track & Field",
    36: "Volleyball",
    37: "Water Polo",
    38: "Wrestling",
    39: "Boxing",
    42: "Dance",
    43: "Pilates",
    44: "Yoga",
    45: "Weightlifting",
    47: "Cross Country Skiing",
    48: "Functional Fitness",
    49: "Duathlon",
    51: "Gymnastics",
    52: "Hiking/Rucking",
    53: "Horseback Riding",
    55: "Kayaking",
    56: "Martial Arts",
    57: "Mountain Biking",
    59: "Powerlifting",
    60: "Rock Climbing",
    61: "Paddleboarding",
    62: "Triathlon",
    63: "Walking",
    64: "Surfing",
    65: "Elliptical",
    66: "Stairmaster",
    70: "Meditation",
    71: "Other",
    73: "Diving",
    74: "Operations - Tactical",
    75: "Operations - Medical",
    76: "Operations - Flying",
    77: "Operations - Water",
    82: "Ultimate",
    83: "Climber",
    84: "Jumping Rope",
    85: "Australian Football",
    86: "Skateboarding",
    87: "Coaching",
    88: "Ice Bath",
    89: "Commuting",
    90: "Gaming",
    91: "Snowboarding",
    92: "Motocross",
    93: "Caddying",
    94: "Obstacle Course Racing",
    95: "Motor Racing",
    96: "HIIT",
    97: "Spin",
    98: "Jiu Jitsu",
    99: "Manual Labor",
    100: "Cricket",
    101: "Pickleball",
    102: "Inline Skating",
    103: "Box Fitness",
    104: "Spikeball",
    105: "Wheelchair Pushing",
    106: "Paddle Tennis",
    107: "Barre",
    108: "Stage Performance",
    109: "High Stress Work",
    110: "Parkour",
    111: "Gaelic Football",
    112: "Hurling/Camogie",
    113: "Circus Arts",
    121: "Massage Therapy",
    125: "Watching Sports",
    126: "Assault Bike",
    127: "Kickboxing",
    128: "Stretching",
    230: "Table Tennis",
    231: "Badminton",
    232: "Netball",
    233: "Sauna",
    234: "Disc Golf",
    235: "Yard Work",
    236: "Air Compression",
    237: "Percussive Massage",
    238: "Paintball",
    239: "Ice Skating",
    240: "Handball",
}
