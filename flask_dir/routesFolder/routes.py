from flask import Flask, Blueprint, redirect, request_finished, session, request, url_for, render_template
from routesFolder.oauth2 import oauth
from apiRequests import getPlaybackState
from PIL import Image
import urllib.request
import sys
import os
from routesFolder.oauth2 import run_Auth, second_Auth, getToken

sys.path.append("../")

from apiRequests import getUserPlaylists, getUserProfile, getPlaylistDetails, generateBPM, createBPM

secret_key = os.getenv('SECRET')
routes_file = Blueprint("routes_file", __name__)
routes_file.register_blueprint(oauth)
req_token, token_refresh, time_limit, expires_at, headers = "","","", 0, {}

@routes_file.route('/')
@routes_file.route('/index')
def index():
    return render_template('base.html')


#
#       Routes
#

@routes_file.route('/UserPlaylists')
@routes_file.route('/UserPlaylists', methods = ['POST', 'GET'])
def getPlaylists():
    refresh = request.args.get("refresh", default=False, type=bool)
    trackTotal = 50
    offset = request.args.get("offset", default=0, type=int)

    try:
        print("tried")
        token_info = getToken()
    except:
        print("no token", session['req_token'])
        return redirect(url_for('routes_file.oauth.login', external=True))

    # wait for REDIS implementation

    playlists, nextStatus = getUserPlaylists(session['headers'], trackTotal, offset) 

    if request.method == 'POST':
        # only my playlists
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
        
    data = playlists

    # Create potential offset
    potentialOffset = offset + trackTotal

    print(nextStatus)

    return render_template(
        'UserPlaylists.html', 
        data=data, 
        offerOffset = nextStatus,
        offset = potentialOffset )

@routes_file.route('/playlist')
@routes_file.route('/playlist', methods = ['POST', 'GET'])
def playlistDetails():
    playlistHref = request.args.get("href")
    playlistData = getPlaylistDetails(playlistHref, session['headers'])
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

@routes_file.route('/player')
def player():
    response = getPlaybackState(session['headers'])
    try:
        image = response["item"]["album"]['images'][0]['url']
        urllib.request.urlretrieve(
            image, 
            "nowPlaying.jpeg")
        img = Image.open("nowPlaying.jpeg")
        img.convert('RGB')
        width, height = img.size
        red, green, blue = 50, 50, 50
        i = 0
        artist = response["item"]["artists"][0]['name']
        title = response["item"]["name"]
        for x in range(0, width):
            for y in range(0, height):
                if img.getpixel((x,y)) == 255 or img.getpixel((x,y)) == 0:
                    value = img.getpixel((x,y))
                    r, g, b = value, value, value
                else:
                    r, g, b = img.getpixel((x,y))
                red = (red + r)/2
                green = (green + g)/2
                blue = (blue + b)/2
            i += 1
        time = response["item"]["duration_ms"] - response["progress_ms"] + 100
    except Exception as e:
        print(e)
        image = "https://upload.wikimedia.org/wikipedia/commons/a/ac/No_image_available.svg"
        time = 10000
        red, blue, green = 0, 0, 0
        try:
            image = response["item"]["album"]['images'][0]['url']
        except:
            pass
        artist = "no artist"
        title = "no title"
    textColor = "#212121"
    subtitleColor = f"rgb({str(round(red-50, 2))}, {round(blue-50, 2)}, {round(green-50, 2)})"
    if ((red+blue+green) / 3) < 100:
        textColor = "#FFFFFF" 
        subtitleColor = f"rgb({str(round(red+50, 2))}, {round(blue+50, 2)}, {round(green+50, 2)})"

    print(subtitleColor)
    return render_template( "albumCover.html", 
        image = image, 
        time = time, 
        red = red, 
        blue = blue, 
        green = green,
        textColor = textColor,
        subtitleColor = subtitleColor,
        artist = artist,
        title = title,
        )