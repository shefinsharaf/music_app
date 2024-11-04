from flask import Flask, Blueprint, request, redirect, url_for, session, render_template, send_from_directory, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Ensure the directory for uploaded music exists
UPLOAD_FOLDER = 'static/music'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Database initialization function
def init_db():
    conn = sqlite3.connect('music.db')
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL,
                        email TEXT UNIQUE NOT NULL)''')
    
    # Create music table
    cursor.execute('''CREATE TABLE IF NOT EXISTS music (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        artist TEXT NOT NULL,
                        genre TEXT NOT NULL,
                        file_path TEXT NOT NULL)''')
    
    # Create playlists table
    cursor.execute('''CREATE TABLE IF NOT EXISTS playlists (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        name TEXT NOT NULL,
                        description TEXT,
                        FOREIGN KEY(user_id) REFERENCES users(id))''')
    
    # Create playlist_songs table
    cursor.execute('''CREATE TABLE IF NOT EXISTS playlist_songs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        playlist_id INTEGER NOT NULL,
                        music_id INTEGER NOT NULL,
                        FOREIGN KEY(playlist_id) REFERENCES playlists(id),
                        FOREIGN KEY(music_id) REFERENCES music(id))''')
    
    conn.commit()
    conn.close()

# Database helper functions
def get_db():
    conn = sqlite3.connect('music.db')
    conn.row_factory = sqlite3.Row
    return conn

# Authentication routes
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Please fill in all fields', 'error')
            return render_template('login.html')
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Welcome back!', 'success')
            return redirect(url_for('home'))
        
        flash('Invalid username or password', 'error')
        return render_template('login.html')
    
    return render_template('login.html')
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        email = request.form.get('email', '').strip()
        
        # Enhanced input validation
        if not username or not password or not email:
            flash('Please fill in all fields', 'error')
            return render_template('signup.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('signup.html')
        
        if not '@' in email:
            flash('Please enter a valid email address', 'error')
            return render_template('signup.html')
        
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            # Check if username already exists
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                flash('Username already exists', 'error')
                return render_template('signup.html')
            
            # Check if email already exists
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                flash('Email already registered', 'error')
                return render_template('signup.html')
            
            # Create new user
            hashed_password = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO users (username, password, email) VALUES (?, ?, ?)",
                (username, hashed_password, email)
            )
            conn.commit()
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
            
        except sqlite3.Error as e:
            flash(f'An error occurred while creating your account: {str(e)}', 'error')
            return render_template('signup.html')
        finally:
            conn.close()
            
    return render_template('signup.html')
@app.route('/home')
def home():
    if 'user_id' not in session:
        flash('Please log in first', 'error')
        return redirect(url_for('login'))
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Fetch all songs
    cursor.execute("SELECT * FROM music")
    songs = cursor.fetchall()
    
    # Fetch user's playlists
    cursor.execute("SELECT * FROM playlists WHERE user_id = ?", (session['user_id'],))
    playlists = cursor.fetchall()
    
    conn.close()
    return render_template('home.html', songs=songs, playlists=playlists)

@app.route('/create_playlist', methods=['POST'])
def create_playlist():
    if 'user_id' not in session:
        flash('Please log in first', 'error')
        return redirect(url_for('login'))
    
    name = request.form.get('name')
    description = request.form.get('description', '')
    
    if not name:
        flash('Please provide a playlist name', 'error')
        return redirect(url_for('home'))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO playlists (user_id, name, description) VALUES (?, ?, ?)",
        (session['user_id'], name, description)
    )
    conn.commit()
    conn.close()
    
    flash('Playlist created successfully!', 'success')
    return redirect(url_for('home'))

@app.route('/upload_music', methods=['POST'])
def upload_music():
    if 'user_id' not in session:
        flash('Please log in first', 'error')
        return redirect(url_for('login'))
    
    if 'music_file' not in request.files:
        flash('No file uploaded', 'error')
        return redirect(url_for('home'))
    
    file = request.files['music_file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('home'))
    
    title = request.form.get('title')
    artist = request.form.get('artist')
    genre = request.form.get('genre')
    
    if not all([title, artist, genre]):
        flash('Please fill in all fields', 'error')
        return redirect(url_for('home'))
    
    # Save the file
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO music (title, artist, genre, file_path) VALUES (?, ?, ?, ?)",
        (title, artist, genre, file_path)
    )
    conn.commit()
    conn.close()
    
    flash('Music uploaded successfully!', 'success')
    return redirect(url_for('home'))

@app.route('/add_to_playlist', methods=['POST'])
def add_to_playlist():
    if 'user_id' not in session:
        flash('Please log in first', 'error')
        return redirect(url_for('login'))
    
    playlist_id = request.form.get('playlist_id')
    music_id = request.form.get('music_id')
    
    if not playlist_id or not music_id:
        flash('Invalid request', 'error')
        return redirect(url_for('home'))
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Verify playlist belongs to user
    cursor.execute(
        "SELECT user_id FROM playlists WHERE id = ?",
        (playlist_id,)
    )
    playlist = cursor.fetchone()
    
    if not playlist or playlist['user_id'] != session['user_id']:
        flash('Invalid playlist', 'error')
        return redirect(url_for('home'))
    
    try:
        cursor.execute(
            "INSERT INTO playlist_songs (playlist_id, music_id) VALUES (?, ?)",
            (playlist_id, music_id)
        )
        conn.commit()
        flash('Song added to playlist!', 'success')
    except sqlite3.IntegrityError:
        flash('Song already in playlist', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('home'))

## code for songs view inside playlist and remove songs 

@app.route('/playlist/<int:playlist_id>')
def view_playlist(playlist_id):
    conn = get_db()
    cursor = conn.cursor()

    # Get playlist details
    cursor.execute("SELECT name, description FROM playlists WHERE id = ?", (playlist_id,))
    playlist = cursor.fetchone()
    
    # Get songs in the playlist
    cursor.execute("""
        SELECT music.id, music.title, music.artist, music.genre 
        FROM music 
        JOIN playlist_songs ON music.id = playlist_songs.music_id 
        WHERE playlist_songs.playlist_id = ?
    """, (playlist_id,))
    songs = cursor.fetchall()
    
    conn.close()

    if playlist:
        return render_template('select_playlist.html', 
                               playlist_id=playlist_id,  # Pass playlist_id here
                               playlist_name=playlist['name'],
                               playlist_description=playlist['description'],
                               songs=songs)
    else:
        flash('Playlist not found', 'error')
        return redirect(url_for('home'))


@app.route('/remove_song_from_playlist', methods=['POST'])
def remove_song_from_playlist():
    song_id = request.form.get('song_id')
    playlist_id = request.form.get('playlist_id')

    if not song_id or not playlist_id:
        flash('Missing song or playlist ID.', 'error')
        return redirect(url_for('home'))

    conn = get_db()
    cursor = conn.cursor()

    # Remove the song from the playlist
    cursor.execute("DELETE FROM playlist_songs WHERE music_id = ? AND playlist_id = ?", (song_id, playlist_id))
    conn.commit()
    conn.close()

    flash('Song removed from the playlist.', 'success')
    return redirect(url_for('view_playlist', playlist_id=playlist_id))


@app.route('/delete_playlist/<int:playlist_id>', methods=['POST'])
def delete_playlist(playlist_id):
    conn = get_db()
    cursor = conn.cursor()

    # Delete songs from the playlist first
    cursor.execute("DELETE FROM playlist_songs WHERE playlist_id = ?", (playlist_id,))
    
    # Now delete the playlist
    cursor.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
    conn.commit()
    conn.close()

    flash('Playlist deleted successfully.', 'success')
    return redirect(url_for('home'))  # Redirect to home or wherever you want




@app.route('/play/<int:music_id>')
def play_music(music_id):
    if 'user_id' not in session:
        flash('Please log in first', 'error')
        return redirect(url_for('login'))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT file_path FROM music WHERE id = ?", (music_id,))
    music = cursor.fetchone()
    conn.close()
    
    if music:
        return send_from_directory(
            os.path.dirname(music['file_path']),
            os.path.basename(music['file_path'])
        )
    
    flash('Music not found', 'error')
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)