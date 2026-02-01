"""Resource handlers for Whoop API v2.

Copyright (c) 2024 Felix Geilert
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from whoopy.exceptions import ResourceNotFoundError
from whoopy.models import models_v2 as models

if TYPE_CHECKING:
    from whoopy.client_v2 import WhoopClientV2

from .base_v2 import BaseHandler, CollectionHandler, CombinedHandler


class UserHandler(BaseHandler):
    """Handler for user-related endpoints."""

    async def get_profile(self) -> models.UserBasicProfile:
        """Get the authenticated user's basic profile."""
        data = await self._get("user/profile/basic")
        return models.UserBasicProfile(**data)

    async def get_body_measurements(self) -> models.UserBodyMeasurement:
        """Get the authenticated user's body measurements."""
        data = await self._get("user/measurement/body")
        return models.UserBodyMeasurement(**data)


class CycleHandler(CombinedHandler[models.Cycle]):
    """Handler for cycle endpoints."""

    def __init__(self, client: WhoopClientV2):
        """
        Initialize CycleHandler.

        Args:
            client: WhoopClientV2 instance for making API requests
        """
        super().__init__(
            client=client,
            resource_path="cycle",
            collection_path="cycle",
            model_class=models.Cycle,
            response_class=models.PaginatedCycleResponse,  # type: ignore[arg-type]
        )

    async def get_sleep(self, cycle_id: int) -> models.Sleep:
        """
        Get the sleep for a specific cycle.

        Args:
            cycle_id: The cycle ID

        Returns:
            Sleep data for the cycle

        Raises:
            ResourceNotFoundError: If cycle or sleep not found
        """
        try:
            data = await self._get(f"cycle/{cycle_id}/sleep")
            return models.Sleep(**data)
        except Exception as e:
            if "404" in str(e):
                raise ResourceNotFoundError(resource_type="Sleep for Cycle", resource_id=str(cycle_id)) from e
            raise


class SleepHandler(CombinedHandler[models.Sleep]):
    """Handler for sleep endpoints."""

    def __init__(self, client: WhoopClientV2):
        """
        Initialize SleepHandler.

        Args:
            client: WhoopClientV2 instance for making API requests
        """
        super().__init__(
            client=client,
            resource_path="activity/sleep",
            collection_path="activity/sleep",
            model_class=models.Sleep,
            response_class=models.PaginatedSleepResponse,  # type: ignore[arg-type]
        )

    async def get_by_id(self, sleep_id: str | UUID) -> models.Sleep:  # type: ignore[override]
        """
        Get a sleep activity by ID.

        Args:
            sleep_id: The sleep UUID

        Returns:
            Sleep data
        """
        # Convert UUID to string if needed
        if isinstance(sleep_id, UUID):
            sleep_id = str(sleep_id)

        return await super().get_by_id(sleep_id)


class RecoveryHandler(CollectionHandler[models.Recovery]):
    """Handler for recovery endpoints."""

    def __init__(self, client: WhoopClientV2):
        """
        Initialize RecoveryHandler.

        Args:
            client: WhoopClientV2 instance for making API requests
        """
        super().__init__(
            client=client,
            collection_path="recovery",
            model_class=models.Recovery,
            response_class=models.RecoveryCollection,  # type: ignore[arg-type]
        )

    async def get_for_cycle(self, cycle_id: int) -> models.Recovery:
        """
        Get the recovery for a specific cycle.

        Args:
            cycle_id: The cycle ID

        Returns:
            Recovery data for the cycle

        Raises:
            ResourceNotFoundError: If recovery not found
        """
        try:
            data = await self._get(f"cycle/{cycle_id}/recovery")
            return models.Recovery(**data)
        except Exception as e:
            if "404" in str(e):
                raise ResourceNotFoundError(resource_type="Recovery for Cycle", resource_id=str(cycle_id)) from e
            raise


class WorkoutHandler(CombinedHandler[models.WorkoutV2]):
    """Handler for workout endpoints."""

    def __init__(self, client: WhoopClientV2):
        """
        Initialize WorkoutHandler.

        Args:
            client: WhoopClientV2 instance for making API requests
        """
        super().__init__(
            client=client,
            resource_path="activity/workout",
            collection_path="activity/workout",
            model_class=models.WorkoutV2,
            response_class=models.WorkoutCollection,  # type: ignore[arg-type]
        )

    async def get_by_id(self, workout_id: str | UUID) -> models.WorkoutV2:  # type: ignore[override]
        """
        Get a workout by ID.

        Args:
            workout_id: The workout UUID

        Returns:
            Workout data
        """
        # Convert UUID to string if needed
        if isinstance(workout_id, UUID):
            workout_id = str(workout_id)

        return await super().get_by_id(workout_id)

    async def get_by_sport(
        self,
        sport_name: str,
        start: str | datetime | None = None,
        end: str | datetime | None = None,
        limit_per_page: int = 25,
        max_records: int | None = None,
    ) -> list[models.WorkoutV2]:
        """
        Get all workouts for a specific sport.

        Args:
            sport_name: Name of the sport
            start: Start time filter
            end: End time filter
            limit_per_page: Items per page
            max_records: Maximum records to fetch

        Returns:
            List of workouts for the sport
        """
        all_workouts = await self.get_all(start=start, end=end, limit_per_page=limit_per_page, max_records=max_records)

        # Filter by sport name
        sport_name_lower = sport_name.lower()
        return [w for w in all_workouts if w.sport_name.lower() == sport_name_lower]


# Export all handlers
__all__ = [
    "CycleHandler",
    "RecoveryHandler",
    "SleepHandler",
    "UserHandler",
    "WorkoutHandler",
]
