from flask import Flask, Blueprint, redirect, request_finished, session, request, url_for, render_template
import sys
import os
import time
from routesFolder.authScripts import run_Auth, second_Auth, getNewToken

sys.path.append("../")

from apiRequests import getUserPlaylists, getUserProfile, getPlaylistDetails, generateBPM, createBPM

secret_key = os.getenv('SECRET')
routes_file = Blueprint("routes_file", __name__)
req_token, token_refresh, time_limit, expires_at, headers = "","","", 0, {}

@routes_file.route('/')
@routes_file.route('/index')
def index():
    return render_template('base.html')


# OAUTH2.0 authentification & refresh

@routes_file.route('/login')
def login():
    session.clear()
    return spotify_OAuth()

@routes_file.route('/callback')
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
    
    return redirect(url_for('routes_file.getProfile'))

@routes_file.route('/getProfile')
def getProfile():
    user_profile = getUserProfile(session['headers'])
    session['display_name'] = user_profile['display_name']
    session['id'] = user_profile['id']
    session['image_url'] = user_profile['images'][0]

    return redirect(url_for('routes_file.index'))


#
#       Routes
#

@routes_file.route('/UserPlaylists', methods = ['POST', 'GET'])
@routes_file.route('/UserPlaylists')
def getPlaylists():
    refresh = request.args.get("refresh", default=False, type=bool)
    onlyUserCreated = request.args.get("omp", default=False, type=bool)
    try:
        token_info = getToken()
    except:
        print("no token", session['req_token'])
        return redirect(url_for('routes_file.login', external=True))
    
    if not session.get('tokens') or refresh:

        print("200")
        # wait for REDIS implementation
        playlists = getUserPlaylists(session['headers'], 50) # returns dictionary

        if request.method == 'POST':
            if 'omp' in request.form:
                for index, playlist in enumerate(playlists['items']):
                    if playlist['owner']['id'] != session['id']:
                        del playlists['items'][index]
            elif 'refresh' in request.form:
                pass
                # When REDIS is implemented this can be changed
                # playlists = getUserPlaylists(session['headers'], 50)
            else:
                pass
            

        printable = ''
            
        for i in playlists['items']:
            printable += i['name']
            printable += str(i['tracks']['total'])
            printable += '\n'
        printable += str(playlists['total'])
        data = playlists

    return render_template('UserPlaylists.html', data= data)

@routes_file.route('/playlist')
@routes_file.route('/playlist', methods = ['POST', 'GET'])
def playlistDetails():
    playlistUri = request.args.get("uri")
    playlistHref = request.args.get("href")
    playlistData = getPlaylistDetails(playlistUri, playlistHref, session['headers'])
    BPM = False
    GEN = False
    generatedPL = {}
    listOfBPM = []
    dictOfDetails = {}
    if request.method == 'POST':
        if 'BPM' in request.form:
            generatedPL, listOfURI, listOfBPM, dictOfDetails = generateBPM(playlistData, session['headers'])
        elif 'GEN' in request.form:
            generatedPL, listOfURI, listOfBPM, dictOfDetails = generateBPM(playlistData, session['headers'])
            createBPM(listOfURI, playlistData['name'], session['headers'])
        else:
            pass
    # session['currentPlaylist'] = playlist_data
    return render_template(
        'PlaylistDetails.html', 
        playlistData=playlistData,
        generatedPL=generatedPL,
        dictOfDetails=dictOfDetails,
        listOfBPM=listOfBPM
        )


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

