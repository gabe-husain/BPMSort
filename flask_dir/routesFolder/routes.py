# routes.py

from flask import Blueprint, redirect, session, request, url_for, render_template
from PIL import Image
import urllib.request
import colorsys
from typing import Tuple
from .oauth2 import get_token, oauth
from ..main import (
    get_user_playlists, get_user_profile, get_playlist_details,
    generate_bpm, create_bpm_playlist, spotify_request
)

routes_file = Blueprint("routes_file", __name__)

@routes_file.route('/')
@routes_file.route('/index')
def index():
    """Render the index page."""
    return render_template('base.html')

@routes_file.route('/user_playlists', methods=['GET', 'POST'])
def get_playlists():
    """
    Retrieve and display user playlists.
    
    Returns:
        str: Rendered HTML template with playlist data
    """
    try:
        token_info = get_token()
    except Exception:
        return redirect(url_for('oauth.login', external=True))

    limit = 50
    offset = request.args.get("offset", default=0, type=int)

    playlists, next_status = get_user_playlists(session['headers'], limit, offset)

    if request.method == 'POST':
        if 'omp' in request.form:
            playlists['items'] = [p for p in playlists['items'] if p['owner']['id'] == session['id']]

    potential_offset = offset + limit

    return render_template(
        'UserPlaylists.html',
        data=playlists,
        offer_offset=next_status,
        offset=potential_offset
    )

@routes_file.route('/playlist', methods=['GET', 'POST'])
def playlist_details():
    """
    Display playlist details and handle BPM sorting.
    
    Returns:
        str: Rendered HTML template with playlist details
    """
    playlist_href = request.args.get("href")
    playlist_data = get_playlist_details(playlist_href, session['headers'])
    
    generated_pl = {}
    list_of_bpm = []
    dict_of_details = {}

    if request.method == 'POST':
        if 'BPM' in request.form or 'GEN' in request.form:
            generated_pl, list_of_uri, list_of_bpm, dict_of_details = generate_bpm(playlist_data, session['headers'])
            
            if 'GEN' in request.form:
                create_bpm_playlist(list_of_uri, playlist_data['name'], session['headers'])

    return render_template(
        'PlaylistDetails.html',
        playlist_data=playlist_data,
        generated_pl=generated_pl,
        dict_of_details=dict_of_details,
        list_of_bpm=list_of_bpm
    )

@routes_file.route('/player')
def player():
    """
    Render the player page with current playback information.
    
    Returns:
        str: Rendered HTML template with player information
    """
    try:
        response = spotify_request('get', 'me/player/currently-playing', headers=session['headers'])
        
        if response and response.get('item'):
            image_url = response["item"]["album"]['images'][0]['url']
            image_path = "nowPlaying.jpeg"
            urllib.request.urlretrieve(image_url, image_path)

            dominant_color = get_dominant_color(image_path)
            
            artist = response["item"]["artists"][0]['name']
            title = response["item"]["name"]
            time = response["item"]["duration_ms"] - response["progress_ms"] + 100
        else:
            raise Exception("No track currently playing")
    except Exception as e:
        print(f"Error processing playback state: {e}")
        image_url = "https://upload.wikimedia.org/wikipedia/commons/a/ac/No_image_available.svg"
        time = 10000
        dominant_color = (0, 0, 0)
        artist = "No artist"
        title = "No title"

    text_color, subtitle_color = get_text_colors(dominant_color)

    return render_template(
        "albumCover.html",
        image=image_url,
        time=time,
        red=dominant_color[0],
        green=dominant_color[1],
        blue=dominant_color[2],
        text_color=text_color,
        subtitle_color=subtitle_color,
        artist=artist,
        title=title,
    )

def get_dominant_color(image_path: str, k: int = 2) -> Tuple[int, int, int]:
    """
    Find the dominant color in an image using a simple clustering algorithm.

    Args:
        image_path (str): Path to the image file.
        k (int): Number of color clusters to use.

    Returns:
        Tuple[int, int, int]: RGB values of the dominant color.
    """
    img = Image.open(image_path)
    img = img.copy()
    img.thumbnail((100, 100))
    img = img.convert('RGB')
    pixels = list(img.getdata())

    def euclidean_distance(color1, color2):
        return sum((a - b) ** 2 for a, b in zip(color1, color2)) ** 0.5

    def simple_kmeans(pixels, k, max_iterations=20):
        import random
        centroids = random.sample(pixels, k)

        for _ in range(max_iterations):
            clusters = [[] for _ in range(k)]
            for pixel in pixels:
                closest_centroid = min(range(k), key=lambda i: euclidean_distance(pixel, centroids[i]))
                clusters[closest_centroid].append(pixel)

            new_centroids = []
            for cluster in clusters:
                if cluster:
                    new_centroid = tuple(int(sum(col) / len(cluster)) for col in zip(*cluster))
                    new_centroids.append(new_centroid)
                else:
                    new_centroids.append(random.choice(pixels))

            if new_centroids == centroids:
                break

            centroids = new_centroids

        largest_cluster = max(clusters, key=len)
        return tuple(int(sum(col) / len(largest_cluster)) for col in zip(*largest_cluster))

    return simple_kmeans(pixels, k)

def get_text_colors(background_color: Tuple[int, int, int]) -> Tuple[str, str]:
    """
    Calculate appropriate text colors based on the background color.

    Args:
        background_color (Tuple[int, int, int]): RGB values of the background color.

    Returns:
        Tuple[str, str]: Hex color codes for main text and subtitle text.
    """
    r, g, b = background_color
    h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255)

    if l > 0.5:
        text_color = "#212121"
        subtitle_l = max(0, l - 0.2)
    else:
        text_color = "#FFFFFF"
        subtitle_l = min(1, l + 0.2)

    subtitle_r, subtitle_g, subtitle_b = colorsys.hls_to_rgb(h, subtitle_l, s)
    subtitle_color = f"#{int(subtitle_r*255):02x}{int(subtitle_g*255):02x}{int(subtitle_b*255):02x}"

    return text_color, subtitle_color