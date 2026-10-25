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

## Mac player widget

A tiny floating, always-on-top, borderless version of the player (native Swift, ~170 KB, no Python needed).
It logs in to Spotify itself with PKCE, so only the Client ID is needed.

1. In the Spotify Dashboard, add the Redirect URI `http://127.0.0.1:47823/callback`
2. Build it (uses `CLIENT_ID` from `.env` if present): ```widget/build.sh --install```
3. Open `~/Applications/Spoti-Viz.app` and click the widget to log in

Click the ♪ menu bar icon to drop the player down (click again to hide), right-click it for
Preferences (marquee speed and text size, Auto or Custom), Full Screen, Log Out and Quit.
Drag the player anywhere to leave it floating, drag the edges to resize, triple-click for full screen (again or Esc to exit).
It can also be opened from the Dock, Spotlight or Launchpad.
