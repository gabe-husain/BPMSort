# BPMSort
Flask site to reorganize Spotify Playlist by BPM only for now.

To Configure on your device, everything you need to set is in your .env file.

In your .env file (in the BPMSort directory), make sure to include:

Client ID: From Spotify Dashboard 
  
  formatted: ```CLIENT_ID="your_client_id"```

Client Secret From Spotify Dashboard 
  
  formatted:  ```CLIENT_SECRET="your_client_secret"```

Current URL From your hosting service, can also work as localhost or whatever port you decide to run it from. 
  
  formatted:```CURRENT_URL ="http://127.0.0.1:5000/"``` locally, or ```CURRENT_URL ="https://gawesome13.pythonanywhere.com/"``` when hosted

  Spotify no longer accepts `localhost` redirect URIs, so use `127.0.0.1` (or an HTTPS URL when hosted).
  In the Spotify Dashboard, add `<CURRENT_URL>callback` as a Redirect URI, e.g. `http://127.0.0.1:5000/callback`.

Then, make sure that you run your program using the virtualenv provided, activated from BPMSort using ```source venv/bin/activate```, 
make sure that the (cd) is visible to ensure it's running

Next create a new .env file (in flask_dir directory) and set:
```FLASK_APP="flask_app.py"```

Now you can run the program from flask_dir using ```flask run```


## Tests

Smoke tests (no Spotify account needed, the Spotify API is mocked). From the BPMSort directory:
```pip install pytest```
```python -m pytest tests/test_smoke.py```
