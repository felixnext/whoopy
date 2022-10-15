"""Holds data models for the whoop api.

Copyright (c) 2022 Felix Geilert
"""


from abc import abstractclassmethod
from datetime import datetime
from typing import Dict
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
    timezone_offset: str = None
    score_state: str

    @abstractclassmethod
    def _dict_parse(cls, data: Dict):
        return data

    @classmethod
    def from_dict(cls, data: Dict):
        for dt in ["created_at", "updated_at", "start", "end"]:
            if dt in data:
                data[dt] = th.any_to_datetime(
                    datetime.strptime(data[dt], "%Y-%m-%dT%H:%M:%S.%fZ")
                )
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
    end: datetime = None
    score: UserCycleScore = None

    @classmethod
    def _dict_parse(cls, data: Dict):
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

    stage_summary: UserSleepStages = None
    sleep_needed: UserSleepNeed = None
    respiratory_rate: float = None
    sleep_performance_percentage: float = None
    sleep_consistency_percentage: float = None
    sleep_efficiency_percentage: float = None


class UserSleep(UserData):
    """Stores data for user sleep."""

    id: int
    nap: bool
    start: datetime
    end: datetime = None
    score: UserSleepScore = None

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
    spo2_percentage: float = None
    skin_temp_celsius: float = None


class UserRecovery(UserData):
    """Stores data for user recovery."""

    cycle_id: int
    sleep_id: int
    score: UserRecoveryScore

    @classmethod
    def _dict_parse(cls, data: Dict):
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
    distance_meter: float = None
    altitude_gain_meter: float = None
    altitude_change_meter: float = None
    zone_duration: UserWorkoutZoneDuration = None


class UserWorkout(UserData):
    """Stores information about a user workout"""

    id: int
    start: datetime
    end: datetime = None
    sport_id: int
    score: UserWorkoutScore = None

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
    126: "Assault Bike",
    85: "Australian Football",
    107: "Barre",
    16: "Baseball",
    17: "Basketball",
    10: "Box Fitness",
    39: "Boxing",
    93: "Caddying",
    46: "Canoeing",
    113: "Circus Arts",
    83: "Climber",
    87: "Coaching",
    89: "Commuting",
    100: "Cricket",
    47: "Cross Country Skiing",
    1: "Cycling",
    42: "Dance",
    73: "Diving",
    49: "Duathlon",
    65: "Elliptical",
    19: "Fencing",
    20: "Field Hockey",
    21: "Football",
    48: "Functional Fitness",
    111: "Gaelic Football",
    90: "Gaming",
    22: "Golf",
    51: "Gymnastics",
    96: "HIIT",
    109: "High Stress Work",
    52: "Hiking/Rucking",
    53: "Horseback Riding",
    112: "Hurling/Camogie",
    88: "Ice Bath",
    24: "Ice Hockey",
    102: "Inline Skating",
    98: "Jiu Jitsu",
    54: "Jogging",
    84: "Jumping Rope",
    55: "Kayaking",
    127: "Kickboxing",
    25: "Lacrosse",
    50: "Machine Workout",
    99: "Manual Labor",
    56: "Martial Arts",
    121: "Massage Therapy",
    70: "Meditation",
    92: "Motocross",
    95: "Motor Racing",
    57: "Mountain Biking",
    94: "Obstacle Course Racing",
    58: "Obstacle Racing",
    76: "Operations - Flying",
    75: "Operations - Medical",
    74: "Operations - Tactical",
    77: "Operations - Water",
    71: "Other",
    131: "Other - Recovery",
    106: "Paddle Tennis",
    61: "Paddleboarding",
    110: "Parkour",
    101: "Pickleball",
    43: "Pilates",
    72: "Pit Practice",
    67: "Plyometrics",
    59: "Powerlifting",
    116: "Resonance Frequency Breathing",
    60: "Rock Climbing",
    18: "Rowing",
    27: "Rugby",
    0: "Running",
    28: "Sailing",
    69: "Sex",
    86: "Skateboarding",
    29: "Skiing",
    91: "Snowboarding",
    30: "Soccer",
    31: "Softball",
    104: "Spikeball",
    97: "Spin",
    68: "Spinning",
    32: "Squash",
    108: "Stage Performance",
    66: "Stairmaster",
    128: "Stretching",
    64: "Surfing",
    33: "Swimming",
    34: "Tennis",
    35: "Track & Field",
    62: "Triathlon",
    82: "Ultimate",
    36: "Volleyball",
    63: "Walking",
    125: "Watching Sports",
    37: "Water Polo",
    45: "Weightlifting",
    105: "Wheelchair Pushing",
    38: "Wrestling",
    44: "Yoga",
}
