# Overview

You can find the API documentation [here](https://developer.whoop.com/docs/introduction).

## Getting Started

You need to register your application [here](https://developer-dashboard.whoop.com/) and
enter the `client_id`, `client_secret` and `redirect_uri` in the config.json file.
Then you can execute the login by running this app.

## Login

When login is executed you will be redirect to Whoop Grant Page.
After granting access, you need to copy the code from the URL and paste it into the text field below.
Then hit enter to execute the login.

The url will look something like this (copy the bold part):

`http://localhost:1234/?code=`**`j54Y9X...m4`**`&scope=offline%20read...&state=9f..05`
