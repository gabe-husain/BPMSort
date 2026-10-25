from collections import namedtuple
import base64
import hashlib
import os
import secrets
from urllib.parse import urlencode
import requests
from dotenv import load_dotenv

# .env lives in the BPMSort directory, two levels up from this file
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".env"))

# Endpoints
AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
API_URL = 'https://api.spotify.com/v1/'

# Spotify no longer accepts "localhost" redirect URIs, only HTTPS or a loopback IP
DEFAULT_URL = 'http://127.0.0.1:5000/'
REQUEST_TIMEOUT = 10

#init values
scope = 'user-read-email user-top-read playlist-read-private playlist-modify-private playlist-modify-public user-read-currently-playing'

AT_response = namedtuple("AT_response",
    "ACCESS_TOKEN TIME_LIMIT TOKENS HEADERS")


def getClient():
    return os.getenv('CLIENT_ID')

def getSecret():
    return os.getenv('CLIENT_SECRET')

def getCallbackUri():
    '''
    Builds the callback URI from CURRENT_URL, it must match the
    redirect URI registered in the Spotify Dashboard exactly
    '''
    uri = os.getenv('CURRENT_URL') or DEFAULT_URL
    uri = uri.replace('://localhost', '://127.0.0.1')
    # plain http is only allowed for loopback, hosted sites (e.g. pythonanywhere) need https
    if uri.startswith('http://') and not uri.startswith(('http://127.0.0.1', 'http://[::1]')):
        uri = 'https://' + uri[len('http://'):]
    if not uri.endswith('/'):
        uri += '/'
    return uri + "callback"

def generatePKCE():
    '''
    Creates a PKCE code verifier and its S256 code challenge

    :return: (code_verifier, code_challenge)
    :rtype: tuple
    '''
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode('ascii')).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b'=').decode('ascii')
    return code_verifier, code_challenge

def run_Auth(state, code_challenge):
    '''
    Runs the AUTH script

    :param state: Random value, checked again in the callback to prevent CSRF
    :type state: String
    :param code_challenge: PKCE code challenge
    :type code_challenge: String

    :return: Url complete with auth endpoint, the client, callback URI and scope
    '''
    params = {
        'response_type': 'code',
        'client_id': getClient(),
        'redirect_uri': getCallbackUri(),
        'scope': scope,
        'state': state,
        'code_challenge_method': 'S256',
        'code_challenge': code_challenge,
    }
    return AUTH_URL + '?' + urlencode(params)

def second_Auth(code, code_verifier):
    '''
    Takes in an Auth Code and sends a post request to
    Spotify to request a token, time limit,
    tokens dict, headers dict, and refresh token

    :param code: Auth code from the login verification/callback
    :type code: String
    :param code_verifier: PKCE code verifier made at login
    :type code_verifier: String

    :return ACCESS_TOKEN: Token to use for requesting data
    :rtype ACCESS_TOKEN: String
    :return TIME_LIMIT: Seconds limit until the token expires
    :rtype TIME_LIMIT: int
    :return tokens: Used to capture refreshToken
    :rtype tokens: dict
    :return headers: Headers to make requests
    :rtype headers: dict
    '''

    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': getCallbackUri(),
        'code_verifier': code_verifier,
    }

    #Request Access token
    print("Made POST request")
    access_token_response = requests.post(TOKEN_URL, data=data, auth=(getClient(), getSecret()), timeout=REQUEST_TIMEOUT)
    access_token_response.raise_for_status()

    return decodeResponse(access_token_response, True)


def decodeResponse(access_token_response, ref_token = False):
    '''
    Takes in Access token response in json, decodes it and spits it out, this is the version with a refresh token

    :param access_token_response: Response from the token endpoint
    :type access_token_response: requests.Response

    :return ACCESS_TOKEN: Token to use for requesting data
    :rtype ACCESS_TOKEN: String
    :return TIME_LIMIT: Seconds limit until the token expires
    :rtype TIME_LIMIT: int
    :return tokens: Used to capture refreshToken
    :rtype tokens: dict
    :return headers: Headers to make requests
    :rtype headers: dict

    '''
    tokens = access_token_response.json()
    ACCESS_TOKEN = tokens['access_token']
    TIME_LIMIT = tokens["expires_in"]
    headers = {
        'Authorization': 'Bearer ' + ACCESS_TOKEN
    }

    # return based on what's needed, if refresh, then no need for refresh token

    if ref_token:
        REFRESH_TOKEN = tokens['refresh_token']
        return AT_response(ACCESS_TOKEN, TIME_LIMIT, tokens, headers), REFRESH_TOKEN
    else:
        return AT_response(ACCESS_TOKEN, TIME_LIMIT, tokens, headers)


def getNewToken(refreshToken):
    '''
    Takes in a refresh token and spits out a new access token.
    Spotify may rotate the refresh token, if so it's in TOKENS['refresh_token']

    :param refreshToken: Refresh token provided by decoded response
    :type refreshToken: String

    :return ACCESS_TOKEN: Token to use for requesting data
    :rtype ACCESS_TOKEN: String
    :return TIME_LIMIT: Seconds limit until the token expires
    :rtype TIME_LIMIT: int
    :return tokens: Used to capture refreshToken
    :rtype tokens: dict
    :return headers: Headers to make requests
    :rtype headers: dict
    '''

    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refreshToken
    }

    print("Made POST request")
    access_token_response = requests.post(TOKEN_URL, data=data, auth=(getClient(), getSecret()), timeout=REQUEST_TIMEOUT)
    access_token_response.raise_for_status()
    return decodeResponse(access_token_response)
