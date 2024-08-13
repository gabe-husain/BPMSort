# auth_scripts.py

from collections import namedtuple
from flask import Blueprint
import requests
import os
from dotenv import load_dotenv
from urllib.parse import quote
import json

load_dotenv()

CLIENT = os.getenv('CLIENT_ID')
SECRET = os.getenv('CLIENT_SECRET')
CURRENT_URL = os.getenv('CURRENT_URL')

# Endpoints
AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
API_URL = 'https://api.spotify.com/v1/'
URI = CURRENT_URL
callback_uri = URI + "callback"

# Init values
scope = 'user-read-email user-top-read playlist-read-private playlist-modify-private playlist-modify-public user-read-currently-playing'

AT_response = namedtuple("AT_response", "ACCESS_TOKEN TIME_LIMIT TOKENS HEADERS")

def run_auth():
    """
    Construct the Spotify authorization URL.

    Returns:
        str: The complete authorization URL.
    """
    full_url = (f"{AUTH_URL}"
                f"?response_type=code"
                f"&client_id={quote(CLIENT)}"
                f"&redirect_uri={quote(callback_uri)}"
                f"&scope={quote(scope)}"
                f"&state=3256723")
    return full_url

def second_auth(code: str, secret: str):
    """
    Exchange the authorization code for an access token.

    Args:
        code (str): The authorization code received from Spotify.
        secret (str): The client secret.

    Returns:
        Tuple[AT_response, str]: A tuple containing the access token response and refresh token.
    """
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': callback_uri,
        'state': secret
    }

    access_token_response = requests.post(TOKEN_URL, data=data, auth=(CLIENT, SECRET))
    return decode_response(access_token_response, True)

def decode_response(access_token_response, ref_token=False):
    """
    Decode the access token response from Spotify.

    Args:
        access_token_response (requests.Response): The response from the token endpoint.
        ref_token (bool): Whether to include the refresh token in the response.

    Returns:
        Union[Tuple[AT_response, str], AT_response]: The decoded token information.
    """
    tokens = json.loads(access_token_response.text)
    access_token = tokens['access_token']
    time_limit = tokens["expires_in"]
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    if ref_token:
        refresh_token = tokens['refresh_token']
        return AT_response(access_token, time_limit, tokens, headers), refresh_token
    else:
        return AT_response(access_token, time_limit, tokens, headers)

def get_new_token(refresh_token: str):
    """
    Get a new access token using the refresh token.

    Args:
        refresh_token (str): The refresh token to use for getting a new access token.

    Returns:
        AT_response: The new access token information.
    """
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }

    access_token_response = requests.post(TOKEN_URL, data=data, auth=(CLIENT, SECRET))
    return decode_response(access_token_response)