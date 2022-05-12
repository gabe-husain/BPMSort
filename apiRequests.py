from operator import itemgetter
import os
from typing import Any
from urllib import response
from urllib.parse import quote, urlsplit, parse_qs
import json
from flask import url_for, redirect, session
import requests
import time

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

def getUserPlaylists(header=dict, number = 50, offset = 0):
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

    # if there are less than 50 playlists requested, then this will work only once
    if number <= 50:
        working_response = getRemainingPlaylists(header, number, offset)
        
        next_status = working_response['next']
    
    # otherwise, multiple api calls
    
    else:
        # First API Call
        working_response = getRemainingPlaylists(header, 50, offset)
        number -= 50

        next_status = working_response['next']

        while next_status and number > 0:
            decoded_page = tryGetSpotifyRequest(
                    next_status, 
                    headers=header
                )
            
            working_response['items'] += decoded_page['items'][:min(number, 50)]
            number -= len(decoded_page['items'][:min(number, 50)])

            next_status = decoded_page['next']
            print(number)
            

    return working_response, next_status

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

def getPlaylistDetails(href=str, header=dict):
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
    full_response = response
    next = response['tracks']['next']
    while next != None:
        response = tryGetSpotifyRequest(
            next, 
            headers=header)
        next = response['next']
        full_response['tracks']['items'] += response['items']

    return full_response

def getAudioFeatures(listOfTrackIDs=list, header=dict):
    '''
    Takes in a list of tracks, and returns a dictionary containing their audio features

    :param listOfTrackIDs: List of Tracks as returned by the playlist endpoint smaller than 100
    :type listOfTrackIDs: list
    :param header: headers for get request
    :type header: dict
    
    :return: Dictionary of list of audio features
    :rtype: dict

    ---


    '''
    stringListOfTrackIDs = ""

    for track in listOfTrackIDs:
        try:
            stringListOfTrackIDs += track['track']['id'] + ","
        except:
            pass

    # remove comma
    stringListOfTrackIDs = stringListOfTrackIDs[:-1]
    print(stringListOfTrackIDs)

    response = tryGetSpotifyRequest(
        API_URL + 'audio-features', 
        headers=header, 
        params={
            "ids" : stringListOfTrackIDs
            }
        )
    
    return response
    

def generateDetails(
    PLItems=list, 
    sortBy='tempo',
    details=list, 
    averageIgnore=list, 
    header=dict):
    '''
    
    
    '''

 
    # generate trackID list for spotify request
    
    # Clean PLItems
    
    PLItemsLength = len(PLItems)
    fullResponse = {'audio_features': []}
    offset = 0

    while PLItemsLength > 0:

        # set current playlist items to handle
        currPLItems = PLItems[offset : offset + min(100, PLItemsLength)]
        print(currPLItems == PLItems[100 : 200], offset, offset + min(100, PLItemsLength))
        
        
        response = getAudioFeatures(currPLItems, header=header)
        # add to complete response
        fullResponse['audio_features'] += response['audio_features']
        # onto the next 100
        PLItemsLength -= min(100, PLItemsLength)
        offset += 100

        

    # sort audio features
    audio_features = sorted(fullResponse['audio_features'], key=itemgetter(sortBy))
    dictOfDetails = createDictOfDetails(audio_features, details, averageIgnore=averageIgnore)


    listOfTrackIDs = dictOfDetails['id']

    # sort playlist items for representation
    newTracks = sorted(PLItems, key=lambda x: listOfTrackIDs.index(x['track']['id']))

    # Finalize cool list
    SortedBy = dictOfDetails[sortBy]
    dictOfDetails['average' + sortBy] = sum(SortedBy)/len(SortedBy)

    print(dictOfDetails)

    # extract URI
    listOfURI = []
    for track in newTracks:
        listOfURI.append(track['track']['uri'])

    return newTracks, listOfURI, dictOfDetails

def generateBPM(playlistData=dict, header=dict):
    '''
    Creates BPM playlist and returns stuff
    '''
    if playlistData['tracks']['items']:
        PLItems = playlistData['tracks']['items']

    
    newTracks, listOfURI, dictOfDetails = generateDetails(
        PLItems=PLItems,
        details=['id', 'tempo', 'danceability', 'energy', 'loudness'],
        averageIgnore=['id', 'tempo'],
        header=header
    )
    listOfBPM = dictOfDetails['tempo']
    
    return newTracks, listOfURI, listOfBPM, dictOfDetails
    

def createDictOfDetails(audio_features=list, params=dict, averageIgnore=[], average=False):
    '''
    Given a List of dictionaries returned by Spotify, this collects and creates a dictionary of lists 
    where the key is given by a list of params and the list of values is generated
    
    :param audio_features: List of Tracks to filter through
    :type audio_features: dict
    :param params: List of attributes to filter for
    :type params: dict
    :param average: Averages all Details
    :type average: bool
    :param averageIgnore: Creates average but ignores values in list
    :type averageIgnore: list default []

    ---
    :Example:
    >>> createDictOfDetails(audio_features= audioFeatures, params=params, averageIgnore=['id'])
    >>> {'acousticness': 0.00242, 'id': ['2takcwOaAZWiXQijPHIx7B', '2takeOnMeade4WR'], 'energy': 0.842}
    '''
    collectiveDict = {}
    
    for attribute in params:
            # Iterate through the list of parameters
            collectiveDict[attribute] = []
    for track in audio_features:
        # per each track
        for attribute in params:
            # Iterate through the list of parameters
            collectiveDict[attribute] += [track[attribute]]
    
    if average or averageIgnore:
        for attribute in collectiveDict:
            if attribute not in averageIgnore:
                values = collectiveDict[attribute]
                collectiveDict[attribute] = sum(values)/len(values)

    return collectiveDict

def addTracks(playlistID=str, listOfTrackURIs=list, header=dict):
    tryPostSpotifyRequest(
        API_URL + "playlists/" + playlistID + "/tracks",
        headers=header, 
        debug=True,
        json = {
                "uris" : listOfTrackURIs
            }
        )

def createBPM(listOfURIs=str, name=str, header=dict):
    if not session['id']:
        redirect(url_for("routes_file.getProfile", external=True))
    id = session['id']

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
    
    PLItemsLength = len(listOfURIs)
    offset = 0

    while PLItemsLength > 0:
        # set current playlist items to handle
        response = addTracks(
            playlistID, 
            listOfURIs[offset : offset + min(100, PLItemsLength)], 
            header=header)
        # onto the next 100
        PLItemsLength -= min(100, PLItemsLength)


