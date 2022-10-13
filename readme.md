# Whoop Python Client

This is an unofficial implementation of the [official Whoop API](https://developer.whoop.com/docs/introduction).

## Getting Started

First you will need to install the library:

```bash
# either from pypi
pip install whoopy
# or by local build
pip install .
```

In order to use the API, you will need to register your application [here](https://developer-dashboard.whoop.com/) and
enter the `client_id`, `client_secret` and `redirect_uri` in the `config.json` file (you can use the template provided in `config.sample.json`):

```json
{
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "redirect_uri": "YOUR_REDIRECT_URI"
}
```

> Note: For the purposes of local use, you can simply provide `http://localhost:1234` as redirect_uri in the app registration

### Authorization

You can then the config to run through the client authentication and save the token:

```python
# TODO
```

### Data Retrieval

Once you have the client registered you can retrieve the data through the different sub-functions:

```python
# user info
user_data = client.user.profile()
print(f"Name: {user_data.first_name} {user_data.last_name}")
```

## Tools

The repo also contains a dashboard to explore and download your whoop data using streamlit.

To get started, simply install the requirements in the `tools/explorer` folder:

```bash
pip install -r requirements.txt
```

Then run the streamlit app:

```bash
streamlit run explorer.py
```

This should give you the dashboard:
TODO: images