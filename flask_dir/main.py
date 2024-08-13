# main.py

import os
from typing import Any, Dict, List, Tuple, Optional
from urllib.parse import quote
import json
from flask import url_for, redirect, session
import requests
import time
from functools import wraps

API_URL = 'https://api.spotify.com/v1/'

class SpotifyAPIError(Exception):
    """Custom exception for Spotify API errors."""
    pass

def retry_on_failure(max_retries: int = 3, delay: int = 1):
    """
    Decorator to retry a function on failure.

    Args:
        max_retries (int): Maximum number of retry attempts.
        delay (int): Delay between retries in seconds.

    Returns:
        function: Decorated function with retry logic.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    print(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay} seconds...")
                    time.sleep(delay)
        return wrapper
    return decorator

@retry_on_failure(max_retries=3)
def spotify_request(method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
    """
    Make a request to the Spotify API.

    Args:
        method (str): HTTP method ('get' or 'post').
        endpoint (str): The API endpoint (excluding the base URL).
        **kwargs: Additional arguments for the request.

    Returns:
        Dict[str, Any]: JSON response from the API.

    Raises:
        SpotifyAPIError: If the request fails or returns an error status.
    """
    url = f"{API_URL}{endpoint}"
    try:
        if method.lower() == 'get':
            response = requests.get(url, **kwargs)
        elif method.lower() == 'post':
            response = requests.post(url, **kwargs)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise SpotifyAPIError(f"Spotify API request failed: {e}")

def get_user_playlists(header: Dict[str, str], limit: int = 50, offset: int = 0) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Retrieve user playlists from Spotify API.

    Args:
        header (Dict[str, str]): Authorization headers.
        limit (int): Number of playlists to retrieve (max 50).
        offset (int): Starting position for retrieval.

    Returns:
        Tuple[Dict[str, Any], Optional[str]]: Tuple containing playlist data and next page URL (if available).
    """
    params = {
        'limit': min(limit, 50),
        'offset': offset
    }
    
    response = spotify_request('get', 'me/playlists/', headers=header, params=params)
    return response, response.get('next')

def get_user_profile(header: Dict[str, str]) -> Dict[str, Any]:
    """
    Retrieve user profile information from Spotify API.

    Args:
        header (Dict[str, str]): Authorization headers.

    Returns:
        Dict[str, Any]: User profile data.
    """
    return spotify_request('get', 'me/', headers=header)

def get_playlist_details(href: str, header: Dict[str, str]) -> Dict[str, Any]:
    """
    Retrieve detailed information about a specific playlist.

    Args:
        href (str): API endpoint for the playlist.
        header (Dict[str, str]): Authorization headers.

    Returns:
        Dict[str, Any]: Detailed playlist information including all tracks.
    """
    response = spotify_request('get', href, headers=header)
    full_response = response.copy()
    
    while response.get('tracks', {}).get('next'):
        response = spotify_request('get', response['tracks']['next'], headers=header)
        full_response['tracks']['items'].extend(response['items'])
        full_response['tracks']['next'] = response.get('next')

    return full_response

def get_audio_features(track_ids: List[str], header: Dict[str, str]) -> Dict[str, Any]:
    """
    Retrieve audio features for a list of tracks.

    Args:
        track_ids (List[str]): List of Spotify track IDs.
        header (Dict[str, str]): Authorization headers.

    Returns:
        Dict[str, Any]: Audio features for the specified tracks.
    """
    ids_string = ",".join(track_ids)
    return spotify_request('get', 'audio-features', headers=header, params={"ids": ids_string})

def generate_details(header: Dict[str, str], 
                     playlist_items: List[Dict[str, Any]], 
                     sort_by: str = 'tempo',
                     details: List[str] = ['id', 'tempo', 'danceability', 'energy', 'loudness'],
                     average_ignore: List[str] = ['id', 'tempo']) -> Tuple[List[Dict[str, Any]], List[str], Dict[str, Any]]:
    """
    Generate detailed information about tracks in a playlist, including audio features.

    Args:
        header (Dict[str, str]): Authorization headers.
        playlist_items (List[Dict[str, Any]]): List of tracks in the playlist.
        sort_by (str): Audio feature to sort the tracks by.
        details (List[str]): List of audio features to include in the results.
        average_ignore (List[str]): List of features to ignore when calculating averages.

    Returns:
        Tuple[List[Dict[str, Any]], List[str], Dict[str, Any]]:
            - List of tracks sorted by the specified feature
            - List of track URIs
            - Dictionary of audio feature details
    """
    track_ids = [item['track']['id'] for item in playlist_items if item['track']['id']]
    
    audio_features = []
    for i in range(0, len(track_ids), 100):
        chunk = track_ids[i:i+100]
        response = get_audio_features(chunk, header)
        audio_features.extend(response['audio_features'])

    sorted_features = sorted(audio_features, key=lambda x: x.get(sort_by, 0))
    
    details_dict = {detail: [track.get(detail) for track in sorted_features] for detail in details}
    
    for key in details_dict:
        if key not in average_ignore:
            values = [v for v in details_dict[key] if v is not None]
            details_dict[f'average_{key}'] = sum(values) / len(values) if values else 0

    sorted_tracks = sorted(playlist_items, key=lambda x: details_dict['id'].index(x['track']['id']))
    track_uris = [track['track']['uri'] for track in sorted_tracks]

    return sorted_tracks, track_uris, details_dict

def generate_bpm(playlist_data: Dict[str, Any], header: Dict[str, str]) -> Tuple[List[Dict[str, Any]], List[str], List[float], Dict[str, Any]]:
    """
    Generate BPM-sorted playlist data.

    Args:
        playlist_data (Dict[str, Any]): Original playlist data.
        header (Dict[str, str]): Authorization headers.

    Returns:
        Tuple[List[Dict[str, Any]], List[str], List[float], Dict[str, Any]]:
            - Sorted list of tracks
            - List of track URIs
            - List of BPM values
            - Dictionary of audio feature details
    """
    playlist_items = playlist_data['tracks']['items']
    sorted_tracks, track_uris, details_dict = generate_details(
        header,
        playlist_items,
        sort_by='tempo',
        details=['id', 'tempo', 'danceability', 'energy', 'loudness'],
        average_ignore=['id', 'tempo']
    )
    
    return sorted_tracks, track_uris, details_dict['tempo'], details_dict

def create_bpm_playlist(track_uris: List[str], name: str, header: Dict[str, str]) -> str:
    """
    Create a new playlist sorted by BPM.

    Args:
        track_uris (List[str]): List of Spotify track URIs.
        name (str): Name for the new playlist.
        header (Dict[str, str]): Authorization headers.

    Returns:
        str: ID of the newly created playlist.

    Raises:
        SpotifyAPIError: If playlist creation or track addition fails.
    """
    if 'id' not in session:
        raise SpotifyAPIError("User ID not found in session")

    user_id = session['id']
    playlist_name = f"BPM playlist: {name}"

    try:
        # Create new playlist
        response = spotify_request(
            'post',
            f"users/{user_id}/playlists",
            headers=header,
            json={"name": playlist_name, "public": False}
        )
        playlist_id = response['id']

        # Add tracks to the playlist
        for i in range(0, len(track_uris), 100):
            chunk = track_uris[i:i+100]
            spotify_request(
                'post',
                f"playlists/{playlist_id}/tracks",
                headers=header,
                json={"uris": chunk}
            )

        return playlist_id
    except SpotifyAPIError as e:
        raise SpotifyAPIError(f"Failed to create BPM playlist: {e}")

if __name__ == "__main__":
    print("This module contains helper functions for Spotify API interactions.")
    print("It should be imported and used in other parts of the application.")