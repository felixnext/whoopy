"""Some basic unit tests for the client

Copyright 2022 (C) Felix Geilert
"""


from whoopy import WhoopClient


def test_client_url():
    """Test that the client URL is correct"""
    url, state = WhoopClient.auth_url("1234", "5678", "http://localhost:5000")
    assert url == (
        "https://api.prod.whoop.com/oauth/oauth2/auth"
        "?scope=offline read:recovery read:cycles read:sleep read:workout read:profile read:body_measurement"
        f"&client_id=1234&client_secret=5678&state={state}"
        "&redirect_uri=http://localhost:5000&response_type=code"
    )
