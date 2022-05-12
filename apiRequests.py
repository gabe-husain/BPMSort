from operator import itemgetter
import os
from typing import Any
from urllib.parse import quote, urlsplit, parse_qs
import json
from flask import url_for, redirect, session
import requests
import time

from main1 import CLIENT, SECRET

API_URL = 'https://api.spotify.com/v1/'

#GET request format: r = requests.get(API_URL + 'api request', header=header)
#r = requests.get(API_URL + 'me/playlists/', headers=headers)
#response = json.loads(r.text)
#USER_ID = response["items"]
#print(response["href"])

def tryGetSpotifyRequest(uri, retryTime=0, debug=False, **args):
    '''
    Takes in a uri and args, wraps the request for python requests module. 
    This allows for centralized rate limiting controls and more abstraction

    :param uri: The endpoint for request
    :type uri: String
    :param **args: any acommpanying arguments
    :type **args: any, though typically dict

    :return: response decoded
    :rtype: dict 
    '''
    if retryTime == 10:
        print("tried 10 times, didn't work")
        return redirect(url_for('routes_file.index', external=True))
    try:
        r = requests.get(uri, **args)

        if debug:
            print(r.text)

        if r.status_code >= 400:
            raise Exception("Not okay")
        print("Made GET request")
        response = json.loads(r.text)

        return response
    except:
        time.sleep(1)
        tryGetSpotifyRequest(uri, retryTime=retryTime+1, **args)

def tryPostSpotifyRequest(uri, retryTime=0, debug=False, **args):
    '''
    Takes in a uri and args, wraps the request for python requests module. 
    This allows for centralized rate limiting controls and more abstraction

    :param uri: The endpoint for request
    :type uri: String
    :param **args: any acommpanying arguments
    :type **args: any, though typically dict

    :return: response decoded
    :rtype: dict 
    '''
    if retryTime == 1:
        print("tried 1 times, didn't work")
        return redirect(url_for('routes_file.index', external=True))
    try:
        r = requests.post(uri, **args)

        if debug:
            print(r.text)
            print(r.url)

        if r.status_code >= 400:
            raise Exception("Not okay")
        print("Made Post request")
        response = json.loads(r.text)
        return response
    except:
        time.sleep(1)
        tryPostSpotifyRequest(uri, retryTime=retryTime+1, **args)

def getRemainingPlaylists(header=dict, number=int, offset = 0):
    '''
    Single api call to return the 50 playlists or less.

    :param header: headers to be used for the request
    :type header: dict
    :param number: non-null integer smaller or equal to 50 of playlists to request
    :type number: 50 >= int > 0
    :param offset: starting position for request
    :type offset: int

    :return: Spotify Playlists
    :rtype: dict of <=50 items
    ---
    :return example: {
        "href": "",
        "items": [ {} ],
        "limit": int,
        "next": "parsed api req",
        "offset": int,
        "previous": "parsed api req",
        "total": int
        }
    '''
    assert 50 >= number > 0
    params_limit = {
        'limit' : number,
        'offset' : offset
    }
    
    working_response = tryGetSpotifyRequest(
        API_URL + 'me/playlists/', 
        headers=header, 
        params=params_limit)


    return working_response

def getUserPlaylists(header=dict, number = 50):
    '''
    takes in header and non-null number of playlists to return, 
    updates main response and returns the amount specified by repeating api calls

    :param header: headers to be used for the request
    :type header: dict
    :param number: non-null integer of playlists to return
    :type number: 50 >= int > 0

    :return: Spotify Playlists
    :rtype: dict
    ---
    :return example: {
        "href": "",
        "items": [ {} ],
        "limit": int,
        "next": "parsed api req",
        "offset": int,
        "previous": "parsed api req",
        "total": int
        }
    '''
    assert number > 0

    # if there are less than 50 plaulists requested, then this will work only once
    if number <= 50:
        working_response = getRemainingPlaylists(header, number)
    
    # otherwise, multiple api calls
    
    else:
        # First API Call
        working_response = getRemainingPlaylists(header, 50)
        number -= 50

        next_status = working_response['next']

        while next_status and number > 0:
            decoded_page = tryGetSpotifyRequest(
                    next_status, 
                    headers=header
                )
            for i in range(min(number, 50)):
                working_response['items'].append(decoded_page['items'][i])
                number -= 1
            next_status = decoded_page['next']
            print(number)
            

    return working_response

def getUserProfile(header=dict):
    '''
    Makes a request to the me/ endpoint of Spotify to retrieve user data

    :param header: headers to be used for the request
    :type header: dict

    :return: User Profile elements
    :rtype: dict
    ---
    :return example: {
        "country": "string",
        "display_name": "string",
        "email": "string",
        "explicit_content": {},
        "external_urls": {},
        "followers": {},
        "href": "string",
        "id": "string",
        "images": [],
        "product": "string",
        "type": "string",
        "uri": "string"
        }
    '''
    response = tryGetSpotifyRequest(
        API_URL + 'me/', 
        headers=header
        )
    return response

def getPlaylistDetails(uri=str, href=str, header=dict):
    '''
    Takes in an api endpoint for a specific playlist
    Gets a playlist and subsequent tracks and data

    :param uri: Playlist uri
    :type header: String
    :param href: api request can be fed in
    :type header: String
    :param header: headers to be used for the request
    :type header: dict

    :return: User Profile elements
    :rtype: dict
    ---
    :return example: {
    "collaborative": Bool,
    "description": "string",
    "external_urls": {},
    "followers": {},
    "href": "string",
    "id": "string",
    "images": [ {} ],
    "name": "string",
    "owner": { userObj },
    "public": true,
    "snapshot_id": "string",
    "tracks": {
        "href": String,
        "items": [ {} ],
        "limit": int,
        "next": String,
        "offset": int,
        "previous": String,
        "total": int },
    "type": "playlist",
    "uri": String
    }
    '''
    response = tryGetSpotifyRequest(
        href, 
        headers=header
    )
    return response

def generateBPM(playlistData=dict, header=dict):

    listOfTrackIDs = ""
    if len(playlistData['tracks']['items']) < 100:
        for track in playlistData['tracks']['items']:
            listOfTrackIDs += track['track']['id'] + ","
        listOfTrackIDs = listOfTrackIDs[:-1]
        print(listOfTrackIDs)
        response = tryGetSpotifyRequest(
            API_URL + 'audio-features', 
            headers=header, 
            params={
                "ids" : listOfTrackIDs
                }
            )

        # Create cool list of details
        dictOfDetails = {}
        
        response['audio_features'].sort(key=itemgetter('tempo'))

        # Creating item lists
        listOfBPM = []
        listOfDanceability = []
        listOfEnergy = []
        listOfLoudness = []

        listOfTrackIDs = []
        
        trackNumber = 0

        for track in response['audio_features']:
            listOfDanceability.append(track['danceability'])
            listOfEnergy.append(track['energy'])
            listOfBPM.append(track['tempo'])
            listOfLoudness.append(track['loudness'])

            listOfTrackIDs.append(track['id'])
            trackNumber += 1
        # sorted list of IDs
        print(listOfTrackIDs)
        
        newTracks = sorted(playlistData['tracks']['items'], key=lambda x: listOfTrackIDs.index(x['track']['id']))

        # Finalize cool list
        dictOfDetails['averageBPM'] = sum(listOfBPM)/len(listOfBPM)
        dictOfDetails['averageDanceability'] = sum(listOfDanceability)/len(listOfDanceability) * 100
        dictOfDetails['averageEnergy'] = sum(listOfEnergy)/len(listOfEnergy) * 100
        dictOfDetails['averageLoudness'] = sum(listOfLoudness)/len(listOfLoudness) + 10

        print(dictOfDetails)

        # extract URI
        listOfURI = []
        for track in newTracks:
            listOfURI.append(track['track']['uri'])

        return newTracks, listOfURI, listOfBPM, dictOfDetails
    
    else:
        return {}

def createBPM(listOfURIs=str, name=str, header=dict):
    if not session['id']:
        redirect(url_for("routes_file.getProfile", external=True))
    id = session['id']
    URIs = listOfURIs
    print(URIs, "/n/n")
    PLname = "BPM playlist " + name
    response = tryPostSpotifyRequest(
        API_URL + "users/" + id + "/playlists",
        headers=header, 
        debug=True,
        json = {
            "name" : PLname
            }
        )
    print(response.keys())
    playlistID = response['id']
    time.sleep(1)
    addSongs = tryPostSpotifyRequest(
        API_URL + "playlists/" + playlistID + "/tracks",
        headers=header, 
        debug=True,
        json={
            "uris" : URIs
        }
        )
    print(str(addSongs), '/n/n')


