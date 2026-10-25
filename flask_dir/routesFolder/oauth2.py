from flask import Blueprint, render_template, session, request, redirect, url_for, abort
import secrets
import time
from routesFolder.authScripts import run_Auth, second_Auth, getNewToken, generatePKCE
from apiRequests import getUserProfile

oauth = Blueprint("oauth", __name__)

@oauth.route('/login')
def login():
    session.clear()
    return spotify_OAuth()

@oauth.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("routes_file.index"))

@oauth.route('/callback')
def retrieveCode():

    # state must match the one made at login, otherwise this could be a forged request
    expected_state = session.pop("oauth_state", None)
    code_verifier = session.pop("code_verifier", None)
    if not expected_state or request.args.get("state") != expected_state:
        abort(400, "State mismatch, try logging in again")

    # user denied access or Spotify returned an error
    if request.args.get("error"):
        print("auth error: ", request.args.get("error"))
        return redirect(url_for("routes_file.index"))

    # Retrieve code from URL
    code = request.args.get("code")
    if not code:
        abort(400, "Missing authorization code")

    # load session variables from decoded authentication
    auth_response, session["token_refresh"]  = second_Auth(code, code_verifier)
    storeToken(auth_response)

    return redirect(url_for('oauth.getProfile'))

@oauth.route('/getProfile')
def getProfile():
    user_profile = getUserProfile(session['headers'])
    session['display_name'] = user_profile['display_name']
    session['id'] = user_profile['id']
    images = user_profile.get('images') or [None]
    session['image_url'] = images[0]

    return redirect(url_for('routes_file.index'))

#
#       HELPER FUNCTIONS
#

def storeToken(auth_response):
    '''
    Loads session variables from a decoded token response
    '''
    session["req_token"] = auth_response.ACCESS_TOKEN
    session["time_limit"] = auth_response.TIME_LIMIT
    session["token_info"] = auth_response.TOKENS
    session["headers"] = auth_response.HEADERS

    # create expiration date
    session["expires_at"] = int(session['time_limit']) + int(time.time())

def getToken():
    # if token info does not exist, then send back exception
    if not session.get("token_info"):
        print("no token")
        raise Exception("no token")

    # get current time
    now = int(time.time())

    is_expired = session["expires_at"] - now < 60

    if is_expired:
        print("is expired")
        auth_response  = getNewToken(session["token_refresh"])
        storeToken(auth_response)

        # Spotify can hand back a new refresh token, keep the old one otherwise
        if auth_response.TOKENS.get("refresh_token"):
            session["token_refresh"] = auth_response.TOKENS["refresh_token"]

    return session['req_token']

def spotify_OAuth():
    '''
    Runs OAuth2 flow by redirecting to URL constructed to be redirected to callback
    '''
    state = secrets.token_urlsafe(16)
    code_verifier, code_challenge = generatePKCE()
    session["oauth_state"] = state
    session["code_verifier"] = code_verifier
    return redirect(run_Auth(state, code_challenge))
