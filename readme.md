# Notes
- Dockerfile is not included as app setup is quite straightforward.
- API key and URL are hardcoded on purpose.
- "Update" request has larger set of fields on purpose.

# Setup
From project's root:
```
$ python -m venv venv
$ source venv/bin/activate
$ pip install -r requirements.txt
$ ./manage.py migrate
$ ./manage.py createsuperuser
$ ./manage.py runserver
```

# Test
`geo.postman_collection.json` is a collection of request that can be imported to Postman.

Use the "Get access token" request to obtain a token. Modify the body with superuser's credentials created during the setup.

Once you got access and refresh tokens, copy access token value to Authorization header like so:
"Bearer + <access_token>"

When a token expires, you can either create a new one using the same process or receive a new one by using the "Refresh access token" request with refresh token from the previous step.
