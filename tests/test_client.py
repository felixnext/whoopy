"""Some basic unit tests for the client

Copyright 2022 (C) Felix Geilert
"""


from whoopy import WhoopClient


def test_client_url():
    """Test that the client URL is correct"""
    url = WhoopClient.auth_url("1234", "5678", "http://localhost:5000")
    assert url == (
        "https://api.prod.whoop.com/oauth/oauth2/authorize?"
        "client_id=1234&redirect_uri=http%3A%2F%2Flocalhost%3A5000&"
        "response_type=code&scope=offline+read%3Arecovery+read%3Acycles"
        "+read%3Asleep+read%3Aworkout+read%3Aprofile+read%3Abody_measurement&"
        "state=5678"
    )
