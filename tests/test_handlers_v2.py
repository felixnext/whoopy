"""Unit tests for Whoop API v2 handlers.

Copyright (c) 2024 Felix Geilert
"""

import pytest
from aioresponses import aioresponses

from whoopy.client_v2 import WhoopClientV2
from whoopy.models.models_v2 import ScoreState
from whoopy.utils import TokenInfo


class TestUserHandler:
    """Test UserHandler functionality."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        token_info = TokenInfo(
            access_token="test_token",
            expires_in=3600,
            refresh_token=None,
            scopes=["read:profile", "read:body_measurement"],
        )
        return WhoopClientV2(token_info=token_info)

    @pytest.mark.asyncio
    async def test_get_profile(self, client):
        """Test getting user profile."""
        async with client as whoop:
            with aioresponses() as m:
                profile_data = {"user_id": 12345, "email": "test@example.com", "first_name": "John", "last_name": "Doe"}

                m.get("https://api.prod.whoop.com/developer/v2/user/profile/basic", payload=profile_data)

                profile = await whoop.user.get_profile()

                assert profile.user_id == 12345
                assert profile.email == "test@example.com"
                assert profile.first_name == "John"
                assert profile.last_name == "Doe"

    @pytest.mark.asyncio
    async def test_get_body_measurements(self, client):
        """Test getting body measurements."""
        async with client as whoop:
            with aioresponses() as m:
                measurement_data = {"height_meter": 1.80, "weight_kilogram": 75.5, "max_heart_rate": 190}

                m.get("https://api.prod.whoop.com/developer/v2/user/measurement/body", payload=measurement_data)

                measurements = await whoop.user.get_body_measurements()

                assert measurements.height_meter == 1.80
                assert measurements.weight_kilogram == 75.5
                assert measurements.max_heart_rate == 190


class TestCycleHandler:
    """Test CycleHandler functionality."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        token_info = TokenInfo(
            access_token="test_token", expires_in=3600, refresh_token=None, scopes=["read:cycles", "read:sleep"]
        )
        return WhoopClientV2(token_info=token_info)

    @pytest.mark.asyncio
    async def test_get_cycle_by_id(self, client):
        """Test getting single cycle by ID."""
        async with client as whoop:
            with aioresponses() as m:
                cycle_data = {
                    "id": 12345,
                    "user_id": 67890,
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T12:00:00Z",
                    "start": "2024-01-01T00:00:00Z",
                    "end": "2024-01-01T23:59:59Z",
                    "timezone_offset": "-05:00",
                    "score_state": "SCORED",
                    "score": {"strain": 10.5, "kilojoule": 2000.0, "average_heart_rate": 120, "max_heart_rate": 180},
                }

                m.get("https://api.prod.whoop.com/developer/v2/cycle/12345", payload=cycle_data)

                cycle = await whoop.cycles.get_by_id(12345)

                assert cycle.id == 12345
                assert cycle.user_id == 67890
                assert cycle.score_state == ScoreState.SCORED
                assert cycle.score.strain == 10.5
                assert cycle.is_complete is True

    @pytest.mark.asyncio
    async def test_get_cycle_collection(self, client):
        """Test getting cycle collection with pagination."""
        async with client as whoop:
            with aioresponses() as m:
                page1_data = {
                    "records": [
                        {
                            "id": 1,
                            "user_id": 100,
                            "created_at": "2024-01-01T00:00:00Z",
                            "updated_at": "2024-01-01T00:00:00Z",
                            "start": "2024-01-01T00:00:00Z",
                            "timezone_offset": "-05:00",
                            "score_state": "SCORED",
                        },
                        {
                            "id": 2,
                            "user_id": 100,
                            "created_at": "2024-01-02T00:00:00Z",
                            "updated_at": "2024-01-02T00:00:00Z",
                            "start": "2024-01-02T00:00:00Z",
                            "timezone_offset": "-05:00",
                            "score_state": "SCORED",
                        },
                    ],
                    "next_token": "token123",
                }

                page2_data = {
                    "records": [
                        {
                            "id": 3,
                            "user_id": 100,
                            "created_at": "2024-01-03T00:00:00Z",
                            "updated_at": "2024-01-03T00:00:00Z",
                            "start": "2024-01-03T00:00:00Z",
                            "timezone_offset": "-05:00",
                            "score_state": "SCORED",
                        }
                    ],
                    "next_token": None,
                }

                # First page (with limit parameter)
                m.get("https://api.prod.whoop.com/developer/v2/cycle?limit=25", payload=page1_data)

                # Second page (with limit and nextToken)
                m.get("https://api.prod.whoop.com/developer/v2/cycle?limit=25&nextToken=token123", payload=page2_data)

                # Get all cycles
                cycles = await whoop.cycles.get_all()

                assert len(cycles) == 3
                assert cycles[0].id == 1
                assert cycles[1].id == 2
                assert cycles[2].id == 3

    @pytest.mark.asyncio
    async def test_get_sleep_for_cycle(self, client):
        """Test getting sleep for a specific cycle."""
        async with client as whoop:
            with aioresponses() as m:
                sleep_data = {
                    "id": "12345678-1234-5678-1234-567812345678",
                    "user_id": 100,
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T08:00:00Z",
                    "start": "2024-01-01T00:00:00Z",
                    "end": "2024-01-01T08:00:00Z",
                    "timezone_offset": "-05:00",
                    "nap": False,
                    "score_state": "SCORED",
                }

                m.get("https://api.prod.whoop.com/developer/v2/cycle/12345/sleep", payload=sleep_data)

                sleep = await whoop.cycles.get_sleep(12345)

                assert str(sleep.id) == "12345678-1234-5678-1234-567812345678"
                assert sleep.nap is False
                assert sleep.duration_hours == 8.0


class TestSleepHandler:
    """Test SleepHandler functionality."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        token_info = TokenInfo(access_token="test_token", expires_in=3600, refresh_token=None, scopes=["read:sleep"])
        return WhoopClientV2(token_info=token_info)

    @pytest.mark.asyncio
    async def test_get_sleep_by_id(self, client):
        """Test getting sleep by UUID."""
        async with client as whoop:
            with aioresponses() as m:
                sleep_id = "87654321-4321-8765-4321-876543218765"
                sleep_data = {
                    "id": sleep_id,
                    "v1_id": 12345,
                    "user_id": 100,
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T08:00:00Z",
                    "start": "2024-01-01T00:00:00Z",
                    "end": "2024-01-01T08:00:00Z",
                    "timezone_offset": "-05:00",
                    "nap": False,
                    "score_state": "SCORED",
                    "score": {
                        "stage_summary": {
                            "total_in_bed_time_milli": 28800000,
                            "total_awake_time_milli": 1800000,
                            "total_no_data_time_milli": 0,
                            "total_light_sleep_time_milli": 14400000,
                            "total_slow_wave_sleep_time_milli": 7200000,
                            "total_rem_sleep_time_milli": 5400000,
                            "sleep_cycle_count": 4,
                            "disturbance_count": 3,
                        },
                        "sleep_needed": {
                            "baseline_milli": 28800000,
                            "need_from_sleep_debt_milli": 0,
                            "need_from_recent_strain_milli": 0,
                            "need_from_recent_nap_milli": 0,
                        },
                        "respiratory_rate": 16.5,
                        "sleep_performance_percentage": 95.0,
                        "sleep_consistency_percentage": 90.0,
                        "sleep_efficiency_percentage": 93.75,
                    },
                }

                m.get(f"https://api.prod.whoop.com/developer/v2/activity/sleep/{sleep_id}", payload=sleep_data)

                sleep = await whoop.sleep.get_by_id(sleep_id)

                assert str(sleep.id) == sleep_id
                assert sleep.v1_id == 12345
                assert sleep.score.sleep_performance_percentage == 95.0
                assert sleep.score.stage_summary.sleep_efficiency_percentage == 93.75


class TestRecoveryHandler:
    """Test RecoveryHandler functionality."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        token_info = TokenInfo(access_token="test_token", expires_in=3600, refresh_token=None, scopes=["read:recovery"])
        return WhoopClientV2(token_info=token_info)

    @pytest.mark.asyncio
    async def test_get_recovery_for_cycle(self, client):
        """Test getting recovery for a specific cycle."""
        async with client as whoop:
            with aioresponses() as m:
                recovery_data = {
                    "cycle_id": 12345,
                    "sleep_id": "12345678-1234-5678-1234-567812345678",
                    "user_id": 100,
                    "created_at": "2024-01-01T08:00:00Z",
                    "updated_at": "2024-01-01T08:00:00Z",
                    "score_state": "SCORED",
                    "score": {
                        "user_calibrating": False,
                        "recovery_score": 85.0,
                        "resting_heart_rate": 55.0,
                        "hrv_rmssd_milli": 65.5,
                        "spo2_percentage": 98.5,
                        "skin_temp_celsius": 33.2,
                    },
                }

                m.get(
                    "https://api.prod.whoop.com/developer/v2/cycle/12345/recovery",
                    payload=recovery_data,
                )

                recovery = await whoop.recovery.get_for_cycle(12345)

                assert recovery.cycle_id == 12345
                assert recovery.score.recovery_score == 85.0
                assert recovery.score.hrv_rmssd_milli == 65.5


class TestWorkoutHandler:
    """Test WorkoutHandler functionality."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        token_info = TokenInfo(access_token="test_token", expires_in=3600, refresh_token=None, scopes=["read:workout"])
        return WhoopClientV2(token_info=token_info)

    @pytest.mark.asyncio
    async def test_get_workout_by_id(self, client):
        """Test getting workout by UUID."""
        async with client as whoop:
            with aioresponses() as m:
                workout_id = "11111111-2222-3333-4444-555555555555"
                workout_data = {
                    "id": workout_id,
                    "v1_id": 54321,
                    "sport_id": 1,
                    "user_id": 100,
                    "created_at": "2024-01-01T10:00:00Z",
                    "updated_at": "2024-01-01T11:00:00Z",
                    "start": "2024-01-01T10:00:00Z",
                    "end": "2024-01-01T11:00:00Z",
                    "timezone_offset": "-05:00",
                    "sport_name": "running",
                    "score_state": "SCORED",
                    "score": {
                        "strain": 8.5,
                        "average_heart_rate": 145,
                        "max_heart_rate": 185,
                        "kilojoule": 1500.0,
                        "percent_recorded": 98.5,
                        "distance_meter": 8000.0,
                        "altitude_gain_meter": 150.0,
                        "altitude_change_meter": 10.0,
                        "zone_durations": {
                            "zone_zero_milli": 300000,
                            "zone_one_milli": 600000,
                            "zone_two_milli": 900000,
                            "zone_three_milli": 900000,
                            "zone_four_milli": 600000,
                            "zone_five_milli": 300000,
                        },
                    },
                }

                m.get(f"https://api.prod.whoop.com/developer/v2/activity/workout/{workout_id}", payload=workout_data)

                workout = await whoop.workouts.get_by_id(workout_id)

                assert str(workout.id) == workout_id
                assert workout.sport_name == "running"
                assert workout.score.strain == 8.5
                assert workout.score.distance_meter == 8000.0
                assert workout.duration_hours == 1.0

    @pytest.mark.asyncio
    async def test_get_workouts_by_sport(self, client):
        """Test filtering workouts by sport."""
        async with client as whoop:
            with aioresponses() as m:
                workouts_data = {
                    "records": [
                        {
                            "id": "11111111-1111-1111-1111-111111111111",
                            "user_id": 100,
                            "created_at": "2024-01-01T10:00:00Z",
                            "updated_at": "2024-01-01T11:00:00Z",
                            "start": "2024-01-01T10:00:00Z",
                            "end": "2024-01-01T11:00:00Z",
                            "timezone_offset": "-05:00",
                            "sport_name": "running",
                            "score_state": "SCORED",
                        },
                        {
                            "id": "22222222-2222-2222-2222-222222222222",
                            "user_id": 100,
                            "created_at": "2024-01-02T10:00:00Z",
                            "updated_at": "2024-01-02T11:00:00Z",
                            "start": "2024-01-02T10:00:00Z",
                            "end": "2024-01-02T11:00:00Z",
                            "timezone_offset": "-05:00",
                            "sport_name": "cycling",
                            "score_state": "SCORED",
                        },
                        {
                            "id": "33333333-3333-3333-3333-333333333333",
                            "user_id": 100,
                            "created_at": "2024-01-03T10:00:00Z",
                            "updated_at": "2024-01-03T11:00:00Z",
                            "start": "2024-01-03T10:00:00Z",
                            "end": "2024-01-03T11:00:00Z",
                            "timezone_offset": "-05:00",
                            "sport_name": "running",
                            "score_state": "SCORED",
                        },
                    ],
                    "next_token": None,
                }

                m.get("https://api.prod.whoop.com/developer/v2/activity/workout?limit=25", payload=workouts_data)

                # Get only running workouts
                running_workouts = await whoop.workouts.get_by_sport("running")

                assert len(running_workouts) == 2
                assert all(w.sport_name == "running" for w in running_workouts)
