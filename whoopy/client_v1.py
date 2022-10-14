"""Official Whoop API.

Generated against version 1.0 of the API.

Copyright 2022 (C) Felix Geilert
"""

from typing import Tuple, List
from typing_extensions import Self
import webbrowser
import uuid
import requests
import json
import os

from .handlers import handler_v1 as handlers


API_VERSION = "1"
API_BASE = "https://api.prod.whoop.com/"
API_AUTH = f"{API_BASE}oauth/oauth2"
SCOPES = [
    "offline",
    "read:recovery",
    "read:cycles",
    "read:sleep",
    "read:workout",
    "read:profile",
    "read:body_measurement",
]


class WhoopClient:
    def __init__(
        self,
        access_token: str,
        expires_in: int,
        scopes: List[str],
        refresh_token: str = None,
        client_id: str = None,
        client_secret: str = None,
    ):
        """Creates a new WhoopClient.

        Note that when client_id and client_secret are not provided, the refresh function will not work.

        Args:
            access_token (str): The access token.
            expires_in (int): The time until the token expires (in seconds).
            scopes (List[str]): The scopes that the token has.
            refresh_token (str, optional): The refresh token. Defaults to None.
            client_id (str, optional): The client ID. Defaults to None.
            client_secret (str, optional): The client secret. Defaults to None.
        """
        self.token = access_token
        self.expires_in = expires_in
        self.scopes = scopes
        self.refresh_token = refresh_token
        self._client_id = client_id
        self._client_secret = client_secret

        # create a session
        self.user_agent = "Python/3.X (X11; Linux x86_64)"
        self._update_session()

        # create a bunch of handlers
        self.user = handlers.WhoopUserHandler(self)
        self.cycle = handlers.WhoopCycleHandler(self)
        self.sleep = handlers.WhoopSleepHandler(self)
        self.workout = handlers.WhoopWorkoutHandler(self)
        self.recovery = handlers.WhoopRecoveryHandler(self)

    @property
    def _token(self):
        return {
            "access_token": self.token,
            "expires_in": self.expires_in,
            "refresh_token": self.refresh_token,
            "scopes": self.scopes,
        }

    def _update_session(self):
        """Updates the session with the new token."""
        self._base_path = f"{API_BASE}developer/v1"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.token}",
                "User-Agent": self.user_agent,
            }
        )

    def store_token(self, path: str):
        """Stores the token to a file.

        Args:
            path (str): The path to the file (e.g. ".tokens/token.json").
        """
        # verify that folder exists
        base_dir = os.path.dirname(path)
        os.makedirs(base_dir, exist_ok=True)

        # store the token
        with open(path, "w") as f:
            json.dump(self._token, f)

    @classmethod
    def from_token(cls, path: str, client_id: str, client_secret: str) -> Self:
        """Loads a token from a file.

        Args:
            path (str): The path to the file (e.g. ".tokens/token.json").
            client_id (str): The client ID.
            client_secret (str): The client secret.
        """
        with open(path, "r") as f:
            token = json.load(f)
        client = cls(
            token["access_token"],
            token["expires_in"],
            token["scopes"],
            token["refresh_token"],
            client_id,
            client_secret,
        )
        client.refresh()

        return client

    # retrieves the authorization url
    @classmethod
    def auth_url(
        cls,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        state: str = None,
        scopes: List[str] = None,
    ) -> Tuple[str, str]:
        """Generates authorization url for the Whoop API."""
        # check state
        if not state:
            state = str(uuid.uuid4())

        # retrieve the data
        if len(state) < 8:
            raise ValueError("State must be at least 8 characters long")

        # generate the
        scopes = scopes or SCOPES
        scope = " ".join(scopes)
        res = (
            f"{API_AUTH}/auth?"
            f"scope={scope}&"
            f"client_id={client_id}&"
            f"client_secret={client_secret}&"
            f"state={state}&"
            f"redirect_uri={redirect_uri}&"
            "response_type=code"
        )

        return res, state

    @classmethod
    def _parse_token(cls, payload, scopes):
        url = f"{API_AUTH}/token"

        # retrieve the codes
        res = requests.post(url, data=payload)
        if res.status_code != 200:
            raise RuntimeError(f"Authorization failed with code {res.status_code}")
        codes = res.json()
        token_scopes = codes["scope"].split(" ")

        # validate scopes
        if scopes:
            for scope in scopes:
                if scope not in token_scopes:
                    raise ValueError(f"Scope {scope} not granted")

        return codes, token_scopes

    @classmethod
    def authorize(
        cls,
        code: str,
        client_id: str,
        client_secret: str,
        redirect_url: str = "https://jwt.ms/",
        scopes: List[str] = None,
    ) -> Self:
        """Authorize the client with the given code."""
        # generate request using the code
        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_url,
        }
        codes, token_scopes = cls._parse_token(payload, scopes)

        # generate the client
        return cls(
            codes["access_token"],
            codes["expires_in"],
            token_scopes,
            codes.get("refresh_token", None),
            client_id=client_id,
            client_secret=client_secret,
        )

    @classmethod
    def auth_flow(
        cls,
        client_id: str,
        client_secret: str,
        redirect_url: str = "https://jwt.ms/",
        state: str = None,
        scopes: List[str] = None,
    ) -> Self:
        """Runs through the entire auth flow.

        Note: This requires to copy the code query attribute from the resulting redirect url.

        Args:
            client_id (str): The client ID.
            client_secret (str): The client secret.
            redirect_url (str, optional): The redirect URL. Defaults to "https://jwt.ms/".
            state (str, optional): The state passed through to the output of request. Defaults to None.
            scopes (List[str], optional): The scopes to request. Defaults to None.
                (In case of None, all scopes are requested.)

        Returns:
            The client object.
        """
        # retrieve url
        url, state = cls.auth_url(client_id, client_secret, redirect_url, state, scopes)

        # send user to auth and wait for code
        webbrowser.open(url)
        code = input("Copy Code Attribute from URL: ")

        # authorize
        client = cls.authorize(code, client_id, client_secret, redirect_url, scopes)

        # complete
        return client

    def refresh(self):
        """Refreshes the token provided."""
        # verify client is setup correctly
        if self.refresh_token is None:
            raise ValueError("No refresh token provided")
        if self._client_id is None or self._client_secret is None:
            raise ValueError("No client id or secret provided")

        # generate request using the code
        payload = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
        }

        # retrieve the codes
        codes, _ = self._parse_token(payload, self.scopes)

        # update data
        self.token = codes["access_token"]
        self.expires_in = codes["expires_in"]
        self.refresh_token = codes.get("refresh_token", None)

        # update sess
        self._update_session()
