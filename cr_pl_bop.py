""" 
.env file needs to be in the same folder and needs to include the following variables as strings:

cid = <Developer ID>
secret = <Developer Secret>
user = <Spotify User Name>
pl_add = <Spotify Playlist ID in that the songs should be inserted>


"""

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from spotipy.oauth2 import SpotifyOAuth
import argparse
import spotipy.util as util
import random
import os
from dotenv import load_dotenv
from pprint import pprint

scope = "playlist-modify-public user-top-read user-library-read"


def get_args():
  # Get arguments from terminal (playlist ID is mandatory)
  parser = argparse.ArgumentParser(
      description='Insert playlist ID for the algorithm to be based on')
  parser.add_argument('-p', '--playlist', action='append',
                      required=True, help='copy spotify URL and extract ID')
  parser.add_argument('-u', '--spotify_user', action='append',
                      required=False, help='username')
  return parser.parse_args()


def get_recommendations(sp, my_seed_songs, tracks_add):
  # Get recommendations on list of spotify playlists IDs (maximum of 5 at a time due to spotify restrictions)
  results = sp.recommendations(seed_tracks=my_seed_songs, limit=5)
  print("Recommended songs:")
  for i, item in enumerate(results['tracks']):
    print(len(tracks_add), item['name'], '//', item['artists'][0]['name'])
    tracks_add.append(item['id'])
  print()
  return tracks_add


def compare_tracks(tracks, tracks_add):
  # Compare two lists of track IDs and remove duplicates
  for i, item in enumerate(tracks['items']):
    track = item['track']
    for tracks_add_i in tracks_add:
      if track['id'] == tracks_add_i:
        print("Removed: ", tracks_add_i,
              "| remaining: ", len(tracks_add)-1)
        tracks_add.remove(tracks_add_i)
  return tracks_add


def remove_known_tracks(sp, tracks_add, user):
  # Loop through all public playlists of user in order to find tracks that are already known
  print("Removing duplicates...")
  playlists = sp.user_playlists(user)
  for playlist in playlists['items']:
    if playlist['owner']['id'] == user:
      print()
      print(playlist['name'], '> total tracks',
            playlist['tracks']['total'])
      results = sp.playlist(playlist['id'], fields="tracks,next")
      tracks = results['tracks']
      tracks_add = compare_tracks(tracks, tracks_add)
      while tracks['next']:
        tracks = sp.next(tracks)
        compare_tracks(tracks, tracks_add)
  return tracks_add


def get_songs_from_playlist(sp, args, user):
  # Get all track IDs from given playlist to base recommendations upon
  my_seed_songs = []
  playlists = sp.user_playlists(user)
  for playlist in playlists['items']:
    if playlist['id'] == str(args.playlist[0]):
      print(playlist['name'], '> total tracks',
            playlist['tracks']['total'])
      results = sp.playlist(playlist['id'], fields="tracks,next")
      tracks = results['tracks']
      for i, item in enumerate(tracks['items']):
        my_seed_songs.append(item['track']['id'])
      while tracks['next']:
        tracks = sp.next(tracks)
        for i, item in enumerate(tracks['items']):
          my_seed_songs.append(item['track']['id'])
  return my_seed_songs


def main():
  # Automatically fills playlist based on songs in a given playlist
  load_dotenv()
  pl_add = os.getenv("pl_add")
  user = os.getenv("user")
  args = get_args()

  if args.spotify_user != None:
    user = str(args.spotify_user[0])

  print("Selected playlist ID: ", str(args.playlist[0]))
  print()

  token = util.prompt_for_user_token(username=user, scope=scope, client_id=os.getenv(
      "cid"), client_secret=os.getenv("secret"), redirect_uri="http://example.com/callback/")

  if token:
    sp = spotipy.Spotify(auth=token)

    my_seed_songs = get_songs_from_playlist(sp, args, user)

    tracks_add = []
    if len(my_seed_songs) > 200:
      my_seed_songs = my_seed_songs[len(my_seed_songs)-200: len(my_seed_songs)]
    random.shuffle(my_seed_songs)

    for i in range(len(my_seed_songs), len(my_seed_songs)-50, -5):
      my_seed_songs_i = my_seed_songs[i-5:i]
      #print("Seed songs", my_seed_songs_i)
      get_recommendations(sp, my_seed_songs_i, tracks_add)

    print("Number of recommended tracks", len(tracks_add))
    remove_known_tracks(sp, tracks_add, user)
    print("Number of recommended tracks", len(tracks_add))

    random.shuffle(tracks_add)
    while len(tracks_add) > 40:
      tracks_add = tracks_add[:-1]
    try:
      # sp.user_playlist_add_tracks(user, playlist_id=pl_add, tracks=tracks_add)
      sp.playlist_replace_items(playlist_id=pl_add, items=tracks_add)
      print("Successfully added to playlist for user: ", user)
    except:
      print("Error while creating playlist")


if __name__ == '__main__':
  main()
