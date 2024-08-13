# oauth2.py

from flask import Blueprint, session, request, redirect, url_for
import time
from routesFolder.auth_scripts import run_auth, second_auth, get_new_token
from flask_dir.main import get_user_profile
import os

oauth = Blueprint("oauth", __name__)

oauth = Blueprint("oauth", __name__)

@oauth.route('/login')
def login():
    """Initiate the login process."""
    session.clear()
    return spotify_oauth()

@oauth.route('/logout')
def logout():
    """Log out the user by clearing the session."""
    session.clear()
    return redirect(url_for("routes_file.index"))

@oauth.route('/callback')
def retrieve_code():
    """Handle the OAuth callback from Spotify."""
    code = request.args.get("code")
    
    auth_response, session["token_refresh"] = second_auth(code, os.getenv('SECRET_KEY'))

    session["req_token"] = auth_response.ACCESS_TOKEN
    session["time_limit"] = auth_response.TIME_LIMIT
    session["token_info"] = auth_response.TOKENS
    session["headers"] = auth_response.HEADERS

    session["expires_at"] = int(session['time_limit']) + int(time.time())
    
    return redirect(url_for('oauth.get_profile'))

@oauth.route('/get_profile')
def get_profile():
    """Retrieve and store the user's Spotify profile information."""
    user_profile = get_user_profile(session['headers'])
    session['display_name'] = user_profile['display_name']
    session['id'] = user_profile['id']
    session['image_url'] = user_profile['images'][0] if user_profile['images'] else None

    return redirect(url_for('routes_file.index'))

def get_token():
    """
    Retrieve the current access token or refresh if expired.

    Returns:
        str: The current valid access token.

    Raises:
        Exception: If no token info is available in the session.
    """
    if not session.get("token_info"):
        raise Exception("No token info in session")

    now = int(time.time())
    is_expired = session.get("expires_at", 0) - now < 60

    if is_expired:
        auth_response = get_new_token(session["token_refresh"])

        session["req_token"] = auth_response.ACCESS_TOKEN
        session["time_limit"] = auth_response.TIME_LIMIT
        session["token_info"] = auth_response.TOKENS
        session["headers"] = auth_response.HEADERS

        session["expires_at"] = int(session['time_limit']) + int(time.time())
    
    return session['req_token']

def spotify_oauth():
    """
    Initiate the Spotify OAuth flow.

    Returns:
        Response: A redirect to the Spotify authorization URL.
    """
    return redirect(run_auth())