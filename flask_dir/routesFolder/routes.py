from flask import Flask, Blueprint, redirect, request_finished, session, request, url_for, render_template
from apiRequests import getPlaybackState
from PIL import Image
import urllib.request
import sys
import os
from routesFolder.oauth2 import run_Auth, second_Auth, getToken
from apiRequests import getUserPlaylists, getUserProfile, getPlaylistDetails, generateBPM, createBPM
import statistics
import colorsys

secret_key = os.getenv('SECRET')
routes_file = Blueprint("routes_file", __name__)
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
        return redirect(url_for('oauth.login', external=True))

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

from PIL import Image
import urllib.request
import colorsys
import random
import math

def euclidean_distance(color1, color2):
    return sum((a - b) ** 2 for a, b in zip(color1, color2)) ** 0.5

def simple_kmeans(pixels, k=4, max_iterations=20):
    # Randomly initialize centroids
    centroids = random.sample(pixels, k)

    for _ in range(max_iterations):
        # Assign pixels to nearest centroid
        clusters = [[] for _ in range(k)]
        for pixel in pixels:
            closest_centroid = min(range(k), key=lambda i: euclidean_distance(pixel, centroids[i]))
            clusters[closest_centroid].append(pixel)

        # Update centroids
        new_centroids = []
        for cluster in clusters:
            if cluster:
                new_centroid = tuple(int(sum(col) / len(cluster)) for col in zip(*cluster))
                new_centroids.append(new_centroid)
            else:
                new_centroids.append(random.choice(pixels))

        # Check for convergence
        if new_centroids == centroids:
            break

        centroids = new_centroids

    # Find the largest cluster
    largest_cluster = max(clusters, key=len)

    # Return the centroid of the largest cluster
    return tuple(int(sum(col) / len(largest_cluster)) for col in zip(*largest_cluster))

def get_dominant_color(image_path, k=2):
    """
    Find the dominant color in an image using a simple clustering algorithm.

    Args:
    image_path (str): Path to the image file.
    k (int): Number of color clusters to use.

    Returns:
    tuple: RGB values of the dominant color.
    """
    # Open the image and resize it to reduce processing time
    img = Image.open(image_path)
    img = img.copy()  # Create a copy to avoid modifying the original image
    img.thumbnail((100, 100))

    # Convert image to RGB mode if it's not already
    img = img.convert('RGB')

    # Get list of all pixels
    pixels = list(img.getdata())

    # Perform clustering
    dominant_color = simple_kmeans(pixels, k)

    return dominant_color

@routes_file.route('/player')
def player():
    """
    Renders the player page with album cover and song information.

    This function retrieves the current playback state from Spotify,
    downloads the album cover, processes it to determine the dominant color,
    and prepares color schemes for the page. It then renders the albumCover.html
    template with the processed information.

    Returns:
        rendered_template: A Flask response object containing the rendered HTML.
    """
    response = getPlaybackState(session['headers'])
    try:
        image = response["item"]["album"]['images'][0]['url']
        image_path = "nowPlaying.jpeg"
        urllib.request.urlretrieve(image, image_path)

        # Get the dominant color
        red, green, blue = get_dominant_color(image_path)

        artist = response["item"]["artists"][0]['name']
        title = response["item"]["name"]
        time = response["item"]["duration_ms"] - response["progress_ms"] + 100
    except Exception as e:
        print(e)
        image = "https://upload.wikimedia.org/wikipedia/commons/a/ac/No_image_available.svg"
        time = 10000
        red, green, blue = 0, 0, 0
        try:
            image = response["item"]["album"]['images'][0]['url']
        except:
            pass
        artist = "no artist"
        title = "no title"

    # Convert RGB to HSL
    h, l, s = colorsys.rgb_to_hls(red/255, green/255, blue/255)

    # Adjust lightness for subtitle color
    if l > 0.5:
        subtitle_l = max(0, l - 0.2)  # Darker for light backgrounds
    else:
        subtitle_l = min(1, l + 0.2)  # Lighter for dark backgrounds

    # Convert back to RGB
    subtitle_r, subtitle_g, subtitle_b = colorsys.hls_to_rgb(h, subtitle_l, s)
    subtitle_r, subtitle_g, subtitle_b = int(subtitle_r*255), int(subtitle_g*255), int(subtitle_b*255)

    textColor = "#212121" if l > 0.5 else "#FFFFFF"
    subtitleColor = f"rgb({subtitle_r}, {subtitle_g}, {subtitle_b})"

    print(f"Background color: rgb({red}, {green}, {blue})")
    print(f"Subtitle color: {subtitleColor}")

    return render_template("albumCover.html",
        image=image,
        time=time,
        red=red,
        blue=blue,
        green=green,
        textColor=textColor,
        subtitleColor=subtitleColor,
        artist=artist,
        title=title,
    )