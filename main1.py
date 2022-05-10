from collections import namedtuple
from tokenize import String
import requests
import os
from urllib.parse import quote, urlsplit, parse_qs
import json

CLIENT = os.getenv('CLIENT_ID')
SECRET = os.getenv('CLIENT_SECRET')

# Endpoints
AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
API_URL = 'https://api.spotify.com/v1/'
URI = 'http://localhost:5000/'
callback_uri = URI + "callback"

#init values
scope = 'user-read-email user-top-read playlist-read-private playlist-modify-private playlist-modify-public'

AT_response = namedtuple("AT_response", 
    "ACCESS_TOKEN TIME_LIMIT TOKENS HEADERS")

def run_Auth():
    '''
    Runs the AUTH script

    :return: Url complete with auth endpoint, the client, callback URI and scope
    '''
    full_url = (AUTH_URL 
        + '?response_type=code&client_id=' 
        + quote(CLIENT) 
        + '&redirect_uri=' 
        + quote(callback_uri) 
        + '&scope=' 
        + quote(scope))
    return full_url

def second_Auth(code=str, secret=str):
    '''
    Takes in an Auth Code and sends a post request to 
    Spotify to request a token, time limit, 
    tokens dict, headers dict, and refresh token
    
    :param code: Auth code from the login verification/callback
    :type code: String
    :param secret: Client Secret
    :type secret: String

    :return ACCESS_TOKEN: Token to use for requesting data
    :rtype ACCESS_TOKEN: String
    :return TIME_LIMIT: Seconds limit until the token expires
    :rtype TIME_LIMIT: int
    :return tokens: Used to capture refreshToken 
    :rtype tokens: dict
    :return headers: Headers to make requests
    :rtype headers: dict
    '''
    
    data = {'grant_type': 'authorization_code', 'code': code, 'redirect_uri': callback_uri, 'state' : secret}

    #Request Access token
    print("Made POST request")
    access_token_response = requests.post(TOKEN_URL, data=data, verify=False, allow_redirects=False, auth=(CLIENT, SECRET))
    #print(access_token_response.headers)
    print(access_token_response.text)

    return decodeResponse(access_token_response, True)
    
    #GET request format: r = requests.get(API_URL + 'api request', header=header)
    #r = requests.get(API_URL + 'me/playlists/', headers=headers)
    #response = json.loads(r.text)
    #USER_ID = response["items"]
    #print(response["href"])

def decodeResponse(access_token_response=str, ref_token = False):
    '''
    Takes in Access token response in json, decodes it and spits it out, this is the version with a refresh token
    
    :param access_token_response: 
    :type access_token_response: 

    :return ACCESS_TOKEN: Token to use for requesting data
    :rtype ACCESS_TOKEN: String
    :return TIME_LIMIT: Seconds limit until the token expires
    :rtype TIME_LIMIT: int
    :return tokens: Used to capture refreshToken 
    :rtype tokens: dict
    :return headers: Headers to make requests
    :rtype headers: dict

    '''
    tokens = json.loads(access_token_response.text)
    print(tokens)
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
    

def getNewToken(refreshToken=str):
    '''
    Takes in a refresh token and spits out a new access token

    :param refreshToken: Refresh token provided by decoded response
    :type access_token_response: 

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
    access_token_response = requests.post(TOKEN_URL, data=data, auth=(CLIENT, SECRET))
    return decodeResponse(access_token_response)




#Get most listened to music

