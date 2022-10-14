"""Builds the various handlers for the Whoop API.

Copyright (c) 2022 Felix Geilert
"""

from typing import Any, Dict, List, Tuple, Type
import requests

import pandas as pd
import time_helper as th

from ..models import models_v1 as models


class WhoopHandler:
    def __init__(self, client) -> None:
        self.client = client

    def _check_datetime(self, date: str) -> str:
        """Checks if the given date is in the correct format."""
        new_date = th.any_to_datetime(date)

        if date is None:
            raise ValueError(f"Invalid Date provided: {date}")

        # make sure this is converted to correct format used by whoop
        return new_date.isoformat() + "Z"

    def _get(self, path: str, params: dict = None, **kwargs) -> requests.Response:
        """Sends a GET request to the Whoop API."""
        path = f"{self.client._base_path}/{path}"
        return self.client.session.get(path, params=params, **kwargs)

    def _post(self, path: str, data: dict = None, **kwargs) -> requests.Response:
        """Sends a POST request to the Whoop API."""
        path = f"{self.client._base_path}/{path}"
        return self.client.session.post(path, data=data, **kwargs)

    def _verify(self, res: requests.Response) -> Dict[str, Any]:
        """Verifies the response from the Whoop API."""
        if res.status_code != 200:
            raise Exception(f"Whoop API returned status code {res.status_code}.")
        return res.json()


class WhoopUserHandler(WhoopHandler):
    def __init__(self, client) -> None:
        super().__init__(client)

    def profile(self) -> models.UserProfile:
        res = self._get("user/profile/basic")
        data = self._verify(res)

        return models.UserProfile(**data)

    def body_measurements(self) -> models.UserMeasurements:
        res = self._get("user/body_measurements")
        data = self._verify(res)

        return models.UserMeasurements(**data)


class WhoopDataHandler(WhoopHandler):
    """Abstract class that works as a data handler

    Note: '@' symbol is used in the paths to indicate split point for id
    """

    def __init__(
        self,
        client: Any,
        path: str,
        model: Type[models.UserData],
        path_single: str = None,
    ) -> None:
        super().__init__(client)
        self._path = path
        self._path_single = path_single or path + "/@"
        self._model = model

    def _get_data(
        self,
        path: str,
        start: str = None,
        end: str = None,
        next: str = None,
        limit: int = 10,
    ) -> Tuple[Dict, str]:
        """Gets the data from the Whoop API."""
        params = self._params(start, end, next, limit)
        res = self._get(path, params=params)
        data = self._verify(res)
        return data["records"], data.get("next_token")

    def _to_df(self, data: List[models.UserData]) -> pd.DataFrame:
        """Converts the given data to a pandas DataFrame."""
        return pd.json_normalize([d.dict() for d in data])

    def _params(
        self, start: str = None, end: str = None, next: str = None, limit: int = 10
    ) -> Dict[str, Any]:
        # check limit value
        if limit > 25 or limit < 1:
            raise ValueError("Limit must be between 1 and 25.")

        # generate params
        params = {"limit": limit}
        if start:
            params["start"] = self._check_datetime(start)
        if end:
            params["end"] = self._check_datetime(end)
        if next:
            params["nextToken"] = next

        return params

    def single(self, id: int) -> models.UserData:
        """Gets a single data object from the Whoop API."""
        path = self._path_single.split("@", 1)
        path = f"{path[0]}{id}{path[1] if len(path) > 1 else ''}"
        res = self._get(path)
        data = self._verify(res)
        return self._model.from_dict(data)

    def collection(
        self,
        start: str = None,
        end: str = None,
        next: str = None,
        limit: int = 10,
        get_all_pages: bool = True,
    ) -> Tuple[List[models.UserData], str]:
        """Gets a collection of data from the Whoop API."""
        recs, token = self._get_data(self._path, start, end, next, limit)
        items = [self._model.from_dict(c) for c in recs]

        # get more data if there is a next token
        if get_all_pages:
            while token:
                data, token = self.collection(
                    start=start, end=end, next=token, limit=limit, get_all_pages=False
                )
                items.extend(data)

        return items, token

    def collection_df(
        self,
        start: str = None,
        end: str = None,
        next: str = None,
        limit: int = 10,
        get_all_pages: bool = True,
    ) -> Tuple[pd.DataFrame, str]:
        """Gets a collection of data from the Whoop API."""
        recs, token = self.collection(start, end, next, limit, get_all_pages)
        df = self._to_df(recs)

        return df, token

    def latest(self) -> models.UserData:
        """Gets the latest data from the Whoop API."""
        recs, _ = self.collection(limit=1, get_all_pages=False)
        return recs[0]


class WhoopCycleHandler(WhoopDataHandler):
    def __init__(self, client) -> None:
        super().__init__(client, "cycle", models.UserCycle)


class WhoopSleepHandler(WhoopDataHandler):
    def __init__(self, client) -> None:
        super().__init__(client, "activity/sleep", models.UserSleep)


class WhoopRecoveryHandler(WhoopDataHandler):
    def __init__(self, client) -> None:
        super().__init__(client, "recovery", models.UserRecovery, "cycle/@/recovery")


class WhoopWorkoutHandler(WhoopDataHandler):
    def __init__(self, client) -> None:
        super().__init__(client, "activity/workout", models.UserWorkout)
