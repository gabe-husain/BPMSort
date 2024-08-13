from flask import Blueprint, render_template, session, request, redirect, url_for
import time
from routesFolder.authScripts import run_Auth, second_Auth, getNewToken
from apiRequests import getUserProfile
import os

secret_key = os.getenv('SECRET')
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

    # Retrieve code from URL
    code = request.args.get("code")
    
    # load session variables from decoded authentication
    auth_response, session["token_refresh"]  = second_Auth(code, secret_key)

    session["req_token"] = auth_response.ACCESS_TOKEN
    session["time_limit"] = auth_response.TIME_LIMIT
    session["token_info"] = auth_response.TOKENS
    session["headers"] = auth_response.HEADERS

    # create expiration date
    session["expires_at"] = int(session['time_limit']) + int(time.time())
    
    print("req_token: ", session['req_token'])
    
    return redirect(url_for('oauth.getProfile'))

@oauth.route('/getProfile')
def getProfile():
    user_profile = getUserProfile(session['headers'])
    session['display_name'] = user_profile['display_name']
    session['id'] = user_profile['id']
    session['image_url'] = user_profile['images'][0]

    return redirect(url_for('routes_file.index'))

#
#       HELPER FUNCTIONS
#

def getToken():
    # if token info does not exist, then send back exception
    if not session.get("token_info"):
        print("no token")
        raise "exception"

    # get current time
    now = int(time.time())

    print("expires", session["expires_at"], now)

    is_expired = session["expires_at"] - now < 60

    if is_expired:
        print("is expired")
        # load session variables from decoded authentication
        auth_response  = getNewToken(session["token_refresh"])

        session["req_token"] = auth_response.ACCESS_TOKEN
        session["time_limit"] = auth_response.TIME_LIMIT
        session["token_info"] = auth_response.TOKENS
        session["headers"] = auth_response.HEADERS

        # create expiration date
        session["expires_at"] = int(session['time_limit']) + int(time.time())
    
    print('haveToken')
    return session['req_token']

def spotify_OAuth():
    '''
    Runs OAuth2 flow by redirecting to URL constructed to be redirected to callback
    '''
    return redirect(run_Auth())