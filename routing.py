#!/usr/bin/python
####################################
# Created by Max Aaronson
# 3/26/18
####################################

from flask import (Flask,
                   render_template,
                   request,
                   redirect,
                   url_for,
                   flash,
                   jsonify,
                   session as login_session,
                   g,
                   make_response)
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from db_setup import Base, Playlists, Songs
import random
import string
import json
import requests
from oauth2client.client import flow_from_clientsecrets, FlowExchangeError
import httplib2

CLIENT_ID = json.loads(open(
    'client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Playlist App"


app = Flask(__name__)

# SQL engine code
engine = create_engine('postgresql:///playlistdb')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

login = "login"
app.jinja_env.globals.update(login="login")
logout = ""
######################################
# -------- Routing Functions ---------
######################################


# ------------ Main page - View all playlists -------------
@app.route('/')
def mainPage():
    array = session.query(Playlists).order_by(asc(Playlists.name))
    if 'username' not in login_session:
        user_string = "login"
    else:
        user_string = "Logged in as %s" % login_session['username']
    return render_template("main.html", array=array)


# ---------------- Login page ----------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in range(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


# ------------- gconnect -----------------------
@app.route('/gconnect', methods=['GET', 'POST'])
def gconnect():
    # Validate state token
    a = request.args.get('state')
    b = login_session['state']
    print(a)
    print(b)
    if a != b:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
        print("credentials........")
        print(credentials)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    print("access token:")
    print(access_token)
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result, content = h.request(url, 'GET')
    print (result)
    content = json.loads(content.decode('utf-8'))
    print(content)

    # If there was an error in the access token info, abort.
    try:
        error = content['error']
        response = make_response((error), 500)
        response.headers['Content-Type'] = 'application/json'
        return response
    except Exception:
        print("no content")

    # Verify that the access token is used for the intended user.
    gplus_id = int(credentials.id_token['sub'])
    user_id = content['user_id']
    print("gplus_id:")
    print(gplus_id)
    print("user id:")
    print(user_id)
    if str(user_id) != str(gplus_id):
        print("here")
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    issued_to = content['issued_to']
    print ("issued to :")
    print(issued_to)
    print("CLIENT_ID ")
    print(CLIENT_ID)
    if issued_to != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print ("Token's client ID does not match app's.")
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps(
            'Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    app.jinja_env.globals.update(login=login_session['username'])
    app.jinja_env.globals.update(logout="logout")

    output = ''
    output += '<h1>Welcome</h1>'
    return output


# --------------- gdisconnect ----------------
@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session.get('access_token')
    if access_token is None:
        print ('Access Token is None')
        response = make_response(json.dumps(
            'Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    print ('In gdisconnect access token is %s', access_token)
    print ('User name is: ')
    print (login_session['username'])
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % (
        login_session['access_token'])
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print ('result is ')
    print (result)
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        app.jinja_env.globals.update(login="login")
        app.jinja_env.globals.update(logout="")

        return redirect(url_for('mainPage'))
    else:
        response = make_response(json.dumps(
            'Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# ------------ View a playlist -------------
@app.route('/<int:playlist_id>')
def viewPlaylist(playlist_id):
    playlist = session.query(Playlists).filter_by(id=playlist_id).one()
    songs = session.query(Songs).filter_by(playlistId=playlist_id)
    return render_template("playlist.html", songs=songs,
                           playlist_id=playlist_id, playlist=playlist)


# ------------ Add a playlist --------------
@app.route('/add/', methods=['GET', 'POST'])
def addPlaylist():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newPlaylist = Playlists(name=request.form['name'],
                                user_id=login_session['email'])
        session.add(newPlaylist)
        session.commit()
        return redirect(url_for('mainPage'))
    else:
        return render_template("add_playlist.html")


# ------------- Edit a playlist -------------
@app.route('/edit/<int:playlist_id>', methods=['GET', 'POST'])
def editPlaylist(playlist_id):
    if 'username' not in login_session:
        return redirect('/login')
    playlist = session.query(Playlists).filter_by(id=playlist_id).one()
    if login_session['email'] != playlist.user_id:
        flash('You do not own this playlist')
        return render_template('no_auth.html')
    if request.method == 'POST':
        newName = request.form['name']
        playlist.name = newName
        return redirect(url_for('mainPage'))
    else:
        return render_template("edit_playlist.html", playlist=playlist)


# -------------- Delete a playlist -------------
@app.route('/delete/<int:playlist_id>', methods=['GET', 'POST'])
def deletePlaylist(playlist_id):
    if 'username' not in login_session:
        return redirect('/login')
    playlist = session.query(Playlists).filter_by(id=playlist_id).one()
    if login_session['email'] != playlist.user_id:
        flash('You do not own this playlist')
        return render_template('no_auth.html')
    if request.method == 'POST':
        session.delete(playlist)
        session.commit()
        session.flush()
        return redirect(url_for('mainPage'))
    else:
        return render_template("delete_playlist.html", playlist=playlist)


# -------------- View a song --------------------
@app.route('/<int:playlist_id>/<int:song_id>')
def viewSong(playlist_id, song_id):
    song = session.query(Songs).filter_by(playlistId=playlist_id,
                                          id=song_id).one()
    return render_template("view_song.html", song=song,
                           playlist_id=playlist_id, song_id=song_id)


# --------------- Add a song -----------------
@app.route('/add/<int:playlist_id>', methods=['GET', 'POST'])
def addSong(playlist_id):
    if 'username' not in login_session:
        return redirect('/login')
    playlist = session.query(Playlists).filter_by(id=playlist_id).one()
    if login_session['email'] != playlist.user_id:
        flash('You do not own this playlist')
        return render_template('no_auth.html')
    if request.method == 'POST':

        newSong = Songs(title=request.form['title'],
                        artist=request.form['artist'],
                        playlistId=playlist_id,
                        album=request.form['album'],
                        duration=request.form['duration'],
                        artwork=request.form['artwork'],
                        youtubeId=request.form['youtubeId'])

        session.add(newSong)
        session.commit()
        return redirect(url_for('viewPlaylist', playlist_id=playlist_id))
    else:
        return render_template("add_song.html",
                               playlist_id=playlist_id, playlist=playlist)


# --------------- Edit a song ----------------
@app.route('/edit/<int:playlist_id>/<int:song_id>', methods=['GET', 'POST'])
def editSong(playlist_id, song_id):
    if 'username' not in login_session:
        return redirect('/login')
    playlist = session.query(Playlists).filter_by(id=playlist_id).one()
    if login_session['email'] != playlist.user_id:
        flash('You do not own this playlist')
        return render_template('no_auth.html')
    song = session.query(Songs).filter_by(id=song_id).one()
    if request.method == 'POST':
        song.title = request.form['title']
        song.artist = request.form['artist']
        song.album = request.form['album']
        song.duration = request.form['duration']
        song.artwork = request.form['artwork']
        song.youtubeId = request.form['youtubeId']
        session.commit()

        return redirect(url_for('viewPlaylist', playlist_id=playlist_id))
    else:
        return render_template("edit_song.html", playlist_id=playlist_id,
                               song=song)


# --------------- Delete a song -----------------
@app.route('/delete/<int:playlist_id>/<int:song_id>', methods=['GET', 'POST'])
def deleteSong(playlist_id, song_id):
    if 'username' not in login_session:
        return redirect('/login')
    playlist = session.query(Playlists).filter_by(id=playlist_id).one()
    if login_session['email'] != playlist.user_id:
        flash('You do not own this playlist')
        return render_template('no_auth.html')
    playlist = session.query(Playlists).filter_by(id=playlist_id).one()
    songToDelete = session.query(Songs).filter_by(id=song_id).one()
    if request.method == 'POST':
        session.delete(songToDelete)
        session.commit()
        session.flush()
        return redirect(url_for('viewPlaylist', playlist_id=playlist_id))
    else:
        return render_template("delete_song.html", playlist_id=playlist_id,
                               song=songToDelete, playlist=playlist)


# ---------------- JSON endpoints ---------------
@app.route('/json/mainpage')
def jsonMainPage():
    array = session.query(Playlists).order_by(asc(Playlists.name))
    return jsonify(playlists=[p.serialize for p in array])


@app.route('/json/playlist/<int:playlist_id>')
def jsonViewPlaylist(playlist_id):
    playlist = session.query(Playlists).filter_by(id=playlist_id).one()
    songs = session.query(Songs).filter_by(playlistId=playlist_id)
    return jsonify(songs=[s.serialize for s in songs])


@app.route('/json/song/<int:playlist_id>/<int:song_id>')
def jsonViewSong(playlist_id, song_id):
    song = session.query(Songs).filter_by(
        playlistId=playlist_id, id=song_id).one()
    return jsonify(song=song.serialize)


##########################################
# ------------ Run the app --------------#
##########################################
if __name__ == '__main__':
        app.secret_key = 'secret_key'
        app.debug = True
        app.run(host='0.0.0.0', port=8000)
