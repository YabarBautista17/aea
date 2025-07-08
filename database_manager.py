# database_manager.py
# Handles all interactions with the SQLite database (music_library.db).
# Functions for creating tables, adding/updating tracks, managing playlists, etc.

import sqlite3

DB_NAME = "music_library.db"

def create_tables():
    """Creates the necessary database tables if they don't exist."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Tracks table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tracks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filepath TEXT UNIQUE NOT NULL,
        title TEXT,
        artist TEXT,
        album TEXT,
        track_number INTEGER,
        duration REAL,
        date_added TEXT DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%S', 'now')),
        album_art_path TEXT
    )
    """)

    # Playlists table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS playlists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )
    """)

    # Playlist_tracks junction table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS playlist_tracks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        playlist_id INTEGER NOT NULL,
        track_id INTEGER NOT NULL,
        sequence INTEGER NOT NULL,
        FOREIGN KEY (playlist_id) REFERENCES playlists (id) ON DELETE CASCADE,
        FOREIGN KEY (track_id) REFERENCES tracks (id) ON DELETE CASCADE
    )
    """)
    # Consider adding an index for faster playlist track lookups
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_playlist_tracks_playlist_id ON playlist_tracks (playlist_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_playlist_tracks_track_id ON playlist_tracks (track_id)")

    # Indexes for tracks table for faster sorting/searching
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tracks_artist ON tracks (artist)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tracks_album ON tracks (album)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tracks_title ON tracks (title)")


    conn.commit()
    conn.close()
    print(f"Database '{DB_NAME}' and tables checked/created.")

# --- Track Functions ---

def add_track(filepath, title, artist, album, track_number, duration, album_art_path=None):
    """Adds a track to the database. Avoids duplicates based on filepath."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO tracks (filepath, title, artist, album, track_number, duration, album_art_path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (filepath, title, artist, album, track_number, duration, album_art_path))
        conn.commit()
        track_id = cursor.lastrowid
        print(f"Added track: {title} (ID: {track_id})")
        return track_id
    except sqlite3.IntegrityError: # Handles UNIQUE constraint violation for filepath
        print(f"Track already exists (filepath unique): {filepath}")
        cursor.execute("SELECT id FROM tracks WHERE filepath = ?", (filepath,))
        existing_id = cursor.fetchone()
        return existing_id[0] if existing_id else None
    except Exception as e:
        print(f"Error adding track {filepath}: {e}")
        return None
    finally:
        conn.close()

def get_track_by_id(track_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tracks WHERE id = ?", (track_id,))
    track = cursor.fetchone()
    conn.close()
    return track # Returns a tuple or None

def get_all_tracks(sort_by='default'):
    """
    Fetches all tracks.
    sort_by can be 'default' (artist, album, track_number), 'title', 'date_added_newest', 'date_added_oldest'.
    """
    conn = sqlite3.connect(DB_NAME)
    # Return rows as dictionaries for easier access in GUI
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    order_clause = "ORDER BY artist COLLATE NOCASE ASC, album COLLATE NOCASE ASC, track_number ASC, title COLLATE NOCASE ASC"
    if sort_by == 'title':
        order_clause = "ORDER BY title COLLATE NOCASE ASC"
    elif sort_by == 'date_added_newest':
        order_clause = "ORDER BY date_added DESC"
    elif sort_by == 'date_added_oldest':
        order_clause = "ORDER BY date_added ASC"

    cursor.execute(f"SELECT * FROM tracks {order_clause}")
    tracks = cursor.fetchall()
    conn.close()
    return tracks # List of Row objects (dictionary-like)

def get_distinct_artists():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT artist FROM tracks WHERE artist IS NOT NULL ORDER BY artist COLLATE NOCASE ASC")
    artists = [row['artist'] for row in cursor.fetchall()]
    conn.close()
    return artists

def get_distinct_albums(artist_name=None):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if artist_name:
        cursor.execute("""
            SELECT DISTINCT album FROM tracks
            WHERE artist = ? AND album IS NOT NULL
            ORDER BY album COLLATE NOCASE ASC
        """, (artist_name,))
    else:
        cursor.execute("SELECT DISTINCT album FROM tracks WHERE album IS NOT NULL ORDER BY album COLLATE NOCASE ASC")
    albums = [row['album'] for row in cursor.fetchall()]
    conn.close()
    return albums

def get_tracks_by_artist_and_album(artist_name, album_name):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM tracks
        WHERE artist = ? AND album = ?
        ORDER BY track_number ASC, title COLLATE NOCASE ASC
    """, (artist_name, album_name))
    tracks = cursor.fetchall()
    conn.close()
    return tracks

# --- Playlist Functions ---

def create_playlist(name):
    """Creates a new playlist."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO playlists (name) VALUES (?)", (name,))
        conn.commit()
        playlist_id = cursor.lastrowid
        print(f"Created playlist: {name} (ID: {playlist_id})")
        return playlist_id
    except sqlite3.IntegrityError:
        print(f"Playlist '{name}' already exists.")
        cursor.execute("SELECT id FROM playlists WHERE name = ?", (name,))
        existing_id = cursor.fetchone()
        return existing_id[0] if existing_id else None
    except Exception as e:
        print(f"Error creating playlist {name}: {e}")
        return None
    finally:
        conn.close()

def get_all_playlists():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM playlists ORDER BY name COLLATE NOCASE ASC")
    playlists = cursor.fetchall()
    conn.close()
    return playlists # List of Row objects

def add_track_to_playlist(playlist_id, track_id):
    """Adds a track to the end of a playlist."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        # Get current max sequence for this playlist
        cursor.execute("SELECT MAX(sequence) FROM playlist_tracks WHERE playlist_id = ?", (playlist_id,))
        max_seq = cursor.fetchone()[0]
        next_sequence = 0 if max_seq is None else max_seq + 1

        cursor.execute("""
            INSERT INTO playlist_tracks (playlist_id, track_id, sequence)
            VALUES (?, ?, ?)
        """, (playlist_id, track_id, next_sequence))
        conn.commit()
        print(f"Added track ID {track_id} to playlist ID {playlist_id} at sequence {next_sequence}")
        return cursor.lastrowid
    except Exception as e:
        print(f"Error adding track ID {track_id} to playlist ID {playlist_id}: {e}")
        return None
    finally:
        conn.close()

def get_tracks_in_playlist(playlist_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    # Join with tracks table to get full track details
    cursor.execute("""
        SELECT t.*, pt.id as playlist_track_id, pt.sequence
        FROM tracks t
        JOIN playlist_tracks pt ON t.id = pt.track_id
        WHERE pt.playlist_id = ?
        ORDER BY pt.sequence ASC
    """, (playlist_id,))
    tracks = cursor.fetchall()
    conn.close()
    return tracks

def remove_track_from_playlist(playlist_track_id_or_playlist_id, track_id_if_second_arg=None):
    """
    Removes a track from a playlist.
    Can be called with playlist_track_id (from the playlist_tracks table)
    OR with playlist_id and track_id (will remove first occurrence, sequence needs update).
    For simplicity, this version expects playlist_track_id (the PK of the playlist_tracks entry).
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        # This simplified version assumes you have the ID from the playlist_tracks table.
        # A more complex version would handle removing by track_id and playlist_id,
        # and then re-sequencing the playlist, which is non-trivial.
        cursor.execute("DELETE FROM playlist_tracks WHERE id = ?", (playlist_track_id_or_playlist_id,))
        conn.commit()
        if cursor.rowcount > 0:
            print(f"Removed entry ID {playlist_track_id_or_playlist_id} from playlist_tracks.")
            # IMPORTANT: After removing, sequences might need to be updated if they should remain contiguous.
            # This is not handled here for simplicity in this initial implementation.
            return True
        else:
            print(f"No entry found with ID {playlist_track_id_or_playlist_id} in playlist_tracks.")
            return False
    except Exception as e:
        print(f"Error removing entry ID {playlist_track_id_or_playlist_id} from playlist_tracks: {e}")
        return False
    finally:
        conn.close()

def delete_playlist(playlist_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
        # ON DELETE CASCADE should handle playlist_tracks entries
        conn.commit()
        if cursor.rowcount > 0:
            print(f"Deleted playlist ID {playlist_id}.")
            return True
        return False
    except Exception as e:
        print(f"Error deleting playlist ID {playlist_id}: {e}")
        return False
    finally:
        conn.close()


# --- Utility / Maintenance ---
def get_track_count():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tracks")
    count = cursor.fetchone()[0]
    conn.close()
    return count

if __name__ == "__main__":
    create_tables()
    print(f"Database Manager initialized. Track count: {get_track_count()}")

    # Example Usage (for testing this module directly)
    # new_track_id = add_track("/path/to/song.mp3", "Test Song", "Test Artist", "Test Album", 1, 180.5)
    # if new_track_id:
    #     print(f"Track added with ID: {new_track_id}")
    #     track = get_track_by_id(new_track_id)
    #     print(f"Retrieved track: {track}")

    # all_tracks = get_all_tracks()
    # print(f"\nAll Tracks ({len(all_tracks)}):")
    # for t in all_tracks[:5]: # Print first 5
    #     print(f"  {t['artist']} - {t['album']} - {t['track_number']}. {t['title']} ({t['filepath']})")

    # artists = get_distinct_artists()
    # print(f"\nDistinct Artists: {artists}")
    # if artists:
    #     albums_by_first_artist = get_distinct_albums(artists[0])
    #     print(f"Albums by {artists[0]}: {albums_by_first_artist}")
    #     if albums_by_first_artist:
    #         tracks_in_first_album = get_tracks_by_artist_and_album(artists[0], albums_by_first_artist[0])
    #         print(f"Tracks in {artists[0]} - {albums_by_first_artist[0]}:")
    #         for t in tracks_in_first_album:
    #             print(f"  {t['track_number']}. {t['title']}")


    # playlist_id = create_playlist("My Awesome Playlist")
    # if playlist_id and new_track_id:
    #     add_track_to_playlist(playlist_id, new_track_id)
    #     # Add another track if available for testing
    #     # second_track_id = add_track("/path/to/another.mp3", "Another Song", "Another Artist", "Another Album", 1, 200)
    #     # if second_track_id: add_track_to_playlist(playlist_id, second_track_id)

    # playlists = get_all_playlists()
    # print(f"\nAll Playlists: {[p['name'] for p in playlists]}")
    # if playlists:
    #     print(f"Tracks in '{playlists[0]['name']}':")
    #     tracks_in_p = get_tracks_in_playlist(playlists[0]['id'])
    #     for t_in_p in tracks_in_p:
    #         print(f"  Seq {t_in_p['sequence']}: {t_in_p['title']} (Track ID: {t_in_p['id']}, PlaylistTrackID: {t_in_p['playlist_track_id']})")
            # if tracks_in_p: # Test removal
                # remove_track_from_playlist(tracks_in_p[0]['playlist_track_id'])
                # delete_playlist(playlists[0]['id'])

    print("Database Manager - CRUD functions added.")
