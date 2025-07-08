# library_scanner.py
# Scans the music library folder, extracts ID3 tags, and populates the database.

import os
import database_manager # Assumes database_manager.py is in the same directory or Python path

try:
    from mutagen.mp3 import MP3
    from mutagen.id3 import ID3NoHeaderError
    from mutagen import MutagenError
except ImportError:
    print("Mutagen library not found. Please install it with 'pip install mutagen'")
    MP3 = None # Placeholder if mutagen is not installed

# Default music folder path (relative to where downloader.py saves music)
# This might need to be configurable or discovered.
# For now, assume downloader.py is in parent dir or its 'Music' folder is known.
# A more robust solution would involve a config file or user setting.
DEFAULT_MUSIC_ROOT_NAME = "Music" # This is the subfolder created by downloader.py

def get_music_library_path(downloader_script_path=None):
    """
    Determines the path to the music library.
    Assumes the 'Music' folder is in the 'Downloads' directory relative to the user's home
    or in a known location relative to the downloader script if provided.
    This is a simplified assumption.
    """
    # Try user's Downloads/Music path first (consistent with downloader.py's default)
    try:
        if os.name == 'nt':
            import winreg
            sub_key = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders'
            downloads_guid = '{374DE290-123F-4565-9164-39C4925E467B}'
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
                user_downloads_dir = winreg.QueryValueEx(key, downloads_guid)[0]
        else:
            user_downloads_dir = os.path.join(os.path.expanduser('~'), 'Downloads')

        potential_path = os.path.join(user_downloads_dir, DEFAULT_MUSIC_ROOT_NAME)
        if os.path.isdir(potential_path):
            return potential_path
    except Exception as e:
        print(f"Could not determine default downloads path: {e}")

    # Fallback or alternative: if downloader_script_path is given, try relative to it
    if downloader_script_path:
        downloader_dir = os.path.dirname(downloader_script_path)
        potential_path_script_relative = os.path.join(downloader_dir, DEFAULT_MUSIC_ROOT_NAME)
        if os.path.isdir(potential_path_script_relative):
            return potential_path_script_relative

    # Last resort: current_working_directory/Music
    # This is less reliable as cwd can change.
    current_dir_music = os.path.join(os.getcwd(), DEFAULT_MUSIC_ROOT_NAME)
    if os.path.isdir(current_dir_music):
        print(f"Warning: Falling back to CWD/Music: {current_dir_music}")
        return current_dir_music

    print(f"Error: Music library path could not be automatically determined. Please ensure a '{DEFAULT_MUSIC_ROOT_NAME}' folder exists in your Downloads or script directory.")
    return None


def scan_and_populate_library(music_library_path):
    if not MP3:
        print("Mutagen library is required for scanning but not found. Aborting scan.")
        return
    if not music_library_path or not os.path.isdir(music_library_path):
        print(f"Music library path '{music_library_path}' is invalid or does not exist. Aborting scan.")
        return

    print(f"Scanning music library at: {music_library_path}")
    # database_manager.create_tables() should be called once by the main app or when this module is run standalone.

    tracks_added_count = 0
    tracks_skipped_count = 0

    for root, _, files in os.walk(music_library_path):
        for file in files:
            if file.lower().endswith(".mp3"):
                filepath = os.path.join(root, file)

                # Check if already in DB using database_manager function (if we add one)
                # For now, add_track handles unique filepath constraint.
                # existing_track_id = database_manager.get_track_id_by_filepath(filepath) # Hypothetical
                # if existing_track_id:
                #     tracks_skipped_count +=1
                #     continue

                try:
                    audio = MP3(filepath)

                    title_obj = audio.get('TIT2')
                    title = str(title_obj[0]) if title_obj else None

                    artist_obj = audio.get('TPE1')
                    artist = str(artist_obj[0]) if artist_obj else None

                    album_obj = audio.get('TALB')
                    album = str(album_obj[0]) if album_obj else None

                    track_num_obj = audio.get('TRCK')
                    track_number_val = None
                    if track_num_obj:
                        track_number_str = str(track_num_obj[0]).split('/')[0]
                        try:
                            track_number_val = int(track_number_str)
                        except ValueError:
                            pass # Keep as None

                    duration_val = audio.info.length if hasattr(audio, 'info') and hasattr(audio.info, 'length') else 0.0

                    # Fallbacks if ID3 tags are missing
                    path_parts = filepath.replace(music_library_path, '').strip(os.sep).split(os.sep)

                    if not title:
                        title = os.path.splitext(path_parts[-1])[0]
                    if not artist:
                        artist = path_parts[0] if len(path_parts) > 2 else "Unknown Artist"
                    if not album:
                        album = path_parts[1] if len(path_parts) > 2 else "Unknown Album"

                    # print(f"Processing: {artist} - {album} - {title}") # Debug

                    track_id = database_manager.add_track(
                        filepath, title, artist, album,
                        track_number_val, duration_val
                    )
                    if track_id: # add_track returns ID if added or existing
                        # We need to differentiate if it was newly added or just existed.
                        # add_track prints "Track already exists" or "Added track".
                        # For now, we assume if an ID is returned, it's "processed".
                        # A better add_track could return a tuple (id, created_boolean)
                        tracks_added_count +=1 # This counts existing as "added" for now.
                    else: # Should not happen if add_track always returns ID or None for error
                        tracks_skipped_count +=1


                except ID3NoHeaderError:
                    print(f"Warning: No ID3 header in {filepath}. Using filename for title.")
                    title_from_file = os.path.splitext(os.path.basename(filepath))[0]
                    duration_from_info_val = 0.0
                    try:
                        audio_info = MP3(filepath).info
                        duration_from_info_val = audio_info.length
                    except MutagenError:
                        pass # Duration will be 0.0

                    db_id = database_manager.add_track(filepath, title_from_file, "Unknown Artist", "Unknown Album", None, duration_from_info_val)
                    if db_id: tracks_added_count +=1
                    else: tracks_skipped_count +=1
                except MutagenError as e:
                    print(f"Mutagen error processing {filepath}: {e}")
                    tracks_skipped_count +=1
                except Exception as e:
                    print(f"Generic error processing file {filepath}: {e}")
                    tracks_skipped_count +=1

    print(f"Library scan complete. Processed/updated tracks: {tracks_added_count}. Skipped/errored tracks: {tracks_skipped_count}.")


if __name__ == "__main__":
    if MP3 and database_manager:
        database_manager.create_tables() # Ensure DB and tables exist

        downloader_script_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        music_lib_path = get_music_library_path(downloader_script_path=downloader_script_dir)

        if music_lib_path:
            scan_and_populate_library(music_lib_path)
        else:
            print("Could not find music library to scan for standalone test.")
            print(f"Please ensure a '{DEFAULT_MUSIC_ROOT_NAME}' folder exists in Downloads or script directory.")

        print(f"\nTotal tracks in DB after scan: {database_manager.get_track_count()}")
        # Example of how to query (for testing)
        # conn = sqlite3.connect(database_manager.DB_NAME)
        # cursor = conn.cursor()
        # cursor.execute("SELECT artist, album, title FROM tracks ORDER BY artist, album, track_number LIMIT 10")
        # for row in cursor.fetchall():
        #     print(f"DB Query Result: {row}")
        # conn.close()
    else:
        print("Mutagen or database_manager not available. Library Scanner functionality limited.")
    print("Library Scanner - Basic structure (Not yet fully implemented for GUI integration)")
