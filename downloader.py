import subprocess
import os
import argparse
import json
import shutil # For checking ffmpeg path

def check_ffmpeg():
    """Checks if ffmpeg is in PATH and executable."""
    if shutil.which("ffmpeg"):
        return True
    else:
        print("WARNING: ffmpeg not found in PATH. MP3 conversion will likely fail.")
        print("Please install ffmpeg and ensure it is in your system's PATH.")
        print("You can download ffmpeg from https://ffmpeg.org/download.html")
        return False

def get_download_path():
    """Returns the default downloads path for linux or windows"""
    if os.name == 'nt':
        import winreg
        sub_key = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders'
        downloads_guid = '{374DE290-123F-4565-9164-39C4925E467B}'
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
            location = winreg.QueryValueEx(key, downloads_guid)[0]
        return location
    else:
        return os.path.join(os.path.expanduser('~'), 'Downloads')

def download_audio(youtube_url, output_path):
    """
    Downloads audio from a YouTube URL to the specified output path as MP3.
    Uses yt-dlp to handle downloading and conversion.
    """
    music_dir = os.path.join(output_path, "Music")
    os.makedirs(music_dir, exist_ok=True)

def get_video_info(youtube_url, output_path_template):
    """
    Fetches video metadata using yt-dlp without downloading.
    Returns the expected output filepath and title.
    """
    yt_dlp_command = [
        'yt-dlp',
        '-x', '--audio-format', 'mp3', # Define format for filename generation
        '-o', output_path_template,
        '--print', 'json',
        '--simulate', # Simulate download, don't actually download
        '--no-playlist',
        youtube_url
    ]
    print(f"Fetching video info for: {youtube_url}")
    print(f"Command: {' '.join(yt_dlp_command)}")

    title = "Unknown_Title_Due_To_Fetch_Error" # Default title
    simulated_filepath = None

    # First, try to get the filename yt-dlp would use. This is often more resilient.
    filename_command = [
        'yt-dlp', '-x', '--audio-format', 'mp3',
        '-o', output_path_template,
        '--get-filename', # Asks yt-dlp to print the calculated filename
        '--no-playlist',
        youtube_url
    ]
    print(f"Attempting to get filename for: {youtube_url}")
    print(f"Filename command: {' '.join(filename_command)}")
    try:
        filename_result = subprocess.run(filename_command, capture_output=True, text=True, encoding='utf-8', check=False)
        if filename_result.returncode == 0 and filename_result.stdout.strip():
            simulated_filepath = filename_result.stdout.strip()
            # Ensure it has .mp3 extension, as --get-filename might give original ext
            if not simulated_filepath.lower().endswith('.mp3'):
                simulated_filepath = os.path.splitext(simulated_filepath)[0] + '.mp3'
            print(f"Successfully got simulated filename: {simulated_filepath}")

            # Now, try to get the title from JSON metadata if possible (might still fail if main access is blocked)
            yt_dlp_json_command = [
                'yt-dlp', '--print', 'json', '--simulate', '--no-playlist', youtube_url
            ]
            print(f"Attempting to get title from JSON: {' '.join(yt_dlp_json_command)}")
            json_result = subprocess.run(yt_dlp_json_command, capture_output=True, text=True, encoding='utf-8', check=False)
            if json_result.returncode == 0 and json_result.stdout:
                json_output_title = None
                for line in json_result.stdout.strip().split('\n'):
                    if line.strip(): # Find last non-empty line
                        json_output_title = line
                if json_output_title:
                    try:
                        metadata = json.loads(json_output_title)
                        title = metadata.get('title', title) # Update title if found
                        print(f"Successfully fetched title: {title}")
                    except json.JSONDecodeError:
                        print(f"Could not decode JSON for title: {json_output_title[:200]}...") # Print snippet
                else:
                    print("No JSON output for title.")
            else:
                print(f"Could not fetch title JSON. Stderr: {json_result.stderr.strip()}")
        else:
            print(f"Failed to get filename. yt-dlp stderr for filename command:")
            print(filename_result.stderr.strip())
            return None, None # If we can't even get a filename, abort simulation for this URL

    except FileNotFoundError:
        print("Error: yt-dlp command not found.")
        return None, None
    except Exception as e:
        print(f"An unexpected error occurred while fetching info: {e}")
        return None, None

    # If simulated_filepath was successfully obtained, return it and the best title we found
    if simulated_filepath:
        print(f"Final simulated filepath: {simulated_filepath}")
        print(f"Final title: {title}")
        return simulated_filepath, title
    else:
        # This case should ideally be caught by the return within the try block
        print("Failed to determine simulated filepath.")
        return None, None


def download_audio(youtube_url, output_path, simulate_only=False):
    """
    Downloads audio from a YouTube URL to the specified output path as MP3.
    Uses yt-dlp to handle downloading and conversion.
    If simulate_only is True, it will only fetch info and create a dummy file.
    """
    music_dir = os.path.join(output_path, "Music")
    os.makedirs(music_dir, exist_ok=True)

    output_template = os.path.join(music_dir, '%(title)s.%(ext)s')

    if simulate_only:
        print("--- SIMULATION MODE ---")
        simulated_filepath, title = get_video_info(youtube_url, output_template)
        if simulated_filepath and title:
            # Ensure the directory for the simulated file exists
            os.makedirs(os.path.dirname(simulated_filepath), exist_ok=True)
            # Create a dummy file
            with open(simulated_filepath, 'w') as f:
                f.write(f"This is a simulated audio file for '{title}'.\nURL: {youtube_url}\n")
            print(f"Simulated download: Created dummy file for '{title}' at '{simulated_filepath}'")
            return simulated_filepath
        else:
            print("Could not simulate download due to error in fetching info.")
            return None
    else:
        # Actual download logic (currently facing 403 errors)
        yt_dlp_command = [
            'yt-dlp',
            '-x', '--audio-format', 'mp3', '--audio-quality', '0',
            '-o', output_template,
            '--print', 'after_move:filepath',
            '--no-simulate', '--no-playlist',
            # '--extractor-args', 'youtube:player_client=android', # This was still failing
            youtube_url
        ]
        print(f"Attempting to download and convert audio from: {youtube_url}")
        print(f"Command: {' '.join(yt_dlp_command)}")

        try:
            result = subprocess.run(yt_dlp_command, capture_output=True, text=True, encoding='utf-8', check=False)
            if result.returncode == 0:
                final_filepath = None
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        final_filepath = line.strip()

                if final_filepath and os.path.exists(final_filepath):
                    title = os.path.basename(final_filepath)
                    print(f"Successfully downloaded and converted: {title}")
                    print(f"File saved to: {final_filepath}")
                    return final_filepath
                elif final_filepath:
                    print(f"yt-dlp reported path {final_filepath}, but it was not found.")
                    print(f"Full yt-dlp stdout:\n{result.stdout}")
                    print(f"Full yt-dlp stderr:\n{result.stderr}")
                    return None
                else:
                    print("Could not determine downloaded file path from yt-dlp output.")
                    print(f"Full yt-dlp stdout:\n{result.stdout}")
                    print(f"Full yt-dlp stderr:\n{result.stderr}")
                    return None
            else:
                print(f"Error downloading/converting audio (direct YouTube). yt-dlp details:")
                error_output = result.stderr.strip() if result.stderr else ""
                if not error_output and result.stdout.strip(): # If stderr is empty but stdout has info
                    error_output += f"\n(yt-dlp stdout: {result.stdout.strip()})"
                if not error_output: # If both are empty
                    error_output = f"yt-dlp exited with code {result.returncode}."
                print(error_output)
                if "HTTP Error 403" in result.stderr: # Check specifically for 403
                    print("NOTE: This HTTP 403 error likely means YouTube is blocking automated requests from this IP address.")
                    print("Try again later or from a different network/machine.")
                return None
        except FileNotFoundError:
            print("Error: yt-dlp command not found. Please ensure yt-dlp is installed and in your PATH (direct YouTube download).")
            return None
        except Exception as e:
            print(f"An unexpected error occurred during download: {e}")
            if 'result' in locals() and hasattr(result, 'stdout'):
                print(f"Stdout: {result.stdout}")
            if 'result' in locals() and hasattr(result, 'stderr'):
                print(f"Stderr: {result.stderr}")
            return None

if __name__ == "__main__":
    # Preliminary check for ffmpeg
    ffmpeg_available = check_ffmpeg()

    parser = argparse.ArgumentParser(
        description="Download audio from YouTube or Spotify (via YouTube) as MP3.",
        formatter_class=argparse.RawTextHelpFormatter, # To allow newlines in help
        epilog="""
Examples:
  python downloader.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
  python downloader.py "https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT"
  python downloader.py "https://open.spotify.com/album/6reqzBbgKn94X suscitates" --simulate
  python downloader.py "YOUTUBE_OR_SPOTIFY_URL" --output /path/to/my/music
"""
    )
    parser.add_argument("url", help="The YouTube or Spotify URL (track or album).")
    parser.add_argument("--output", help="Optional: The base directory to save music. Defaults to system's Downloads folder.")
    parser.add_argument("--simulate", action="store_true", help="Simulate download: fetch info and create dummy file(s) only.")

    args = parser.parse_args()

    output_directory = args.output if args.output else get_download_path()

    if not output_directory:
        print("Could not determine a default download directory. Please specify with --output.")
        exit(1) # Exit if no output directory

    # Determine URL type
    url_type = None
    if "youtube.com" in args.url or "youtu.be" in args.url:
        url_type = "youtube"
    elif "open.spotify.com" in args.url:
        url_type = "spotify"
    else:
        print("Error: URL must be a valid YouTube or Spotify URL.")
        print(f"Received: {args.url}")
        exit(1) # Exit if URL is not recognized

    if url_type == "youtube":
        if args.simulate:
            print(f"Simulation mode for YouTube URL: Info will be fetched and a dummy file will be created in a 'Music' subdirectory of: {output_directory}")
            download_audio(args.url, output_directory, simulate_only=True)
        else:
            print(f"Output directory for YouTube 'Music': {os.path.join(output_directory, 'Music')}")
            if not ffmpeg_available:
                print("Proceeding with download attempt, but MP3 conversion might fail if yt-dlp cannot use ffmpeg.")
            print("\nNOTE: If downloads from YouTube fail with an HTTP 403 error, it might be due to network restrictions or YouTube blocking automated requests from your IP address. Trying from a different network or your home computer might help.\n")
            download_audio(args.url, output_directory, simulate_only=False)

    elif url_type == "spotify":
        # This will be expanded in the next step
        print(f"Spotify URL detected: {args.url}")
        print("Spotify processing (extracting metadata and then finding on YouTube) will be implemented next.")
        print(f"Simulate mode for Spotify: {args.simulate}")
        # For now, just a message. Later, this will call a new function like handle_spotify_url()
        if not (os.getenv('SPOTIPY_CLIENT_ID') and os.getenv('SPOTIPY_CLIENT_SECRET')):
            print("WARNING: SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET environment variables are not set.")
            print("Spotify functionality will be limited or non-operational.")
            print("Please set them up if you want to process Spotify links.")
        else:
            process_spotify_link(args.url, output_directory, args.simulate, ffmpeg_available)

def sanitize_filename(name):
    """Removes or replaces characters that are problematic in filenames."""
    # Remove characters that are generally problematic on Windows and/or Linux/macOS
    # This is a basic sanitizer, more complex rules could be added.
    name = name.replace('/', '-').replace('\\', '-').replace(':', ' -').replace('*', '_')
    name = name.replace('?', '').replace('"', "'").replace('<', '_').replace('>', '_').replace('|', '_')
    # Limit length to avoid issues with max path lengths, though this is a blunt tool
    return name[:150].strip()

def process_spotify_link(spotify_url, base_output_path, simulate_only, ffmpeg_available):
    """
    Processes a Spotify URL (track or album), fetches metadata,
    searches on YouTube, and then downloads/simulates download.
    """
    print("Processing Spotify link...")
    client_id = os.getenv('SPOTIPY_CLIENT_ID')
    client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')

    if not (client_id and client_secret):
        print("ERROR: SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET environment variables are not set.")
        print("Cannot process Spotify links without these credentials.")
        print("Please refer to Spotipy documentation to get these from https://developer.spotify.com/dashboard/")
        return

    try:
        import spotipy
        from spotipy.oauth2 import SpotifyClientCredentials
        print("Spotipy library imported successfully.")
    except ImportError:
        print("ERROR: The 'spotipy' library is not installed. Please install it with 'pip install spotipy'")
        return

    auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    sp = spotipy.Spotify(auth_manager=auth_manager)

    tracks_to_download = []

    try:
        if "/track/" in spotify_url:
            print("Fetching Spotify track metadata...")
            track_info = sp.track(spotify_url)
            if track_info:
                tracks_to_download.append(track_info)
            else:
                print(f"Could not retrieve metadata for Spotify track: {spotify_url}")
                return
        elif "/album/" in spotify_url:
            print("Fetching Spotify album metadata...")
            album_info = sp.album(spotify_url)
            if not album_info:
                print(f"Could not retrieve metadata for Spotify album: {spotify_url}")
                return

            print(f"Fetching tracks for album: {album_info['name']}")
            results = sp.album_tracks(spotify_url)
            if results:
                tracks_to_download.extend(results['items'])
                # Spotipy's album_tracks handles pagination internally by default for up to 50 tracks.
                # For more, you'd typically loop with sp.next(results) but for most albums, one call is enough.
                # We'll keep it simple for now and assume one page of results is sufficient or that
                # spotipy's default pagination (if any for album_tracks without manual next()) is used.
                # According to docs, album_tracks is paginated. Let's add basic pagination.
                while results['next']:
                    results = sp.next(results)
                    if results and results['items']:
                        tracks_to_download.extend(results['items'])
            else:
                print(f"No tracks found for Spotify album: {spotify_url}")
                return
        else:
            print(f"Unsupported Spotify URL type: {spotify_url}")
            return

        if not tracks_to_download:
            print("No tracks found to process from Spotify URL.")
            return

        print(f"Found {len(tracks_to_download)} track(s) to process from Spotify.")

        for i, track_item in enumerate(tracks_to_download):
            # Track items from album_tracks might be simpler than full track_info objects
            # We might need to call sp.track(track_item['id']) if album_tracks doesn't give enough
            # For now, assume track_item from album_tracks has enough, or it's a full track_info object.

            # Ensure we have a full track object if it's from an album list (which are simplified)
            if 'album' not in track_item : # Simplified track objects from album_tracks might miss album details
                 if track_item.get('id'):
                    print(f"Fetching full track details for: {track_item.get('name', 'Unknown track in album')}")
                    track_item_full = sp.track(track_item['id'])
                    if track_item_full:
                        track_item = track_item_full # Replace with full details
                    else:
                        print(f"Could not get full details for track ID {track_item.get('id')}")
                        continue # Skip this track
                 else:
                    print("Track item from album list is missing ID.")
                    continue


            track_name = track_item.get('name', "Unknown Track")

            # Artists - handle multiple artists
            artists = track_item.get('artists', [])
            artist_names = ", ".join([artist['name'] for artist in artists if artist.get('name')])
            if not artist_names: artist_names = "Unknown Artist"

            album_name = "Unknown Album"
            if track_item.get('album') and track_item['album'].get('name'):
                album_name = track_item['album']['name']

            track_number = track_item.get('track_number', 1)

            print(f"\nProcessing track {i+1}/{len(tracks_to_download)}: {artist_names} - {track_name} (Album: {album_name})")

            # Sanitize components for path creation
            s_artist = sanitize_filename(artist_names.split(',')[0]) # Use primary artist for top-level folder
            s_album = sanitize_filename(album_name)
            # Track name for filename stem will be sanitized just before use in download_youtube_track_for_spotify

            # Output path for this specific track, goes into Artist/Album structure
            # The 'Music' base directory is added by download_audio/get_video_info
            # So, here we define the part *within* 'Music'
            specific_track_output_dir_parts = [s_artist, s_album]

            # The filename itself will be generated by yt-dlp based on the YouTube title,
            # but we want to organize it into these folders.
            # We need to pass a modified output_template to download_audio/get_video_info

            # Construct the search query for YouTube
            search_query = f"{track_name} {artist_names} audio" # Simple query
            print(f"Searching YouTube for: \"{search_query}\"")

            # Use yt-dlp to find the first search result URL (more robust than just ID)
            # ytsearch1: will give the URL of the first result.
            # We use --print "%(webpage_url)s" to get only the URL.
            # --skip-download is crucial here as we only want the URL.
            # --no-warnings to keep output clean
            get_yt_url_command = [
                'yt-dlp',
                '--skip-download',
                '--no-warnings',
                '--print', 'webpage_url', # Print the direct URL of the video
                f"ytsearch1:{search_query}" # Search for one video
            ]

            yt_url_result = subprocess.run(get_yt_url_command, capture_output=True, text=True, encoding='utf-8', check=False)

            youtube_video_url = None
            if yt_url_result.returncode == 0 and yt_url_result.stdout.strip():
                youtube_video_url = yt_url_result.stdout.strip().split('\n')[0] # Take first line if multiple
                print(f"Found YouTube URL: {youtube_video_url}")
            else:
                print(f"Could not find a YouTube video for '{search_query}'.Stderr: {yt_url_result.stderr.strip()}")
                continue # Skip to next track

            # Now download this YouTube URL
            # We need to ensure download_audio uses a path structure like base_output_path/Music/Artist/Album/filename.mp3
            # The current download_audio creates base_output_path/Music/filename.mp3
            # We'll need to adjust how the output_template is constructed or handled.

            # Let's modify the `download_audio_from_youtube` (renamed from download_audio)
            # to accept a more specific output directory *within* the 'Music' folder.

            # The output_path for download_audio should be the 'Music' directory.
            # The actual organization (Artist/Album) will be part of the output template for yt-dlp.

            # Construct the final output directory for this track
            # base_output_path/Music/ARTIST/ALBUM/
            track_specific_music_dir = os.path.join(base_output_path, "Music", s_artist, s_album)
            os.makedirs(track_specific_music_dir, exist_ok=True)

            # The output template for yt-dlp should place it directly in this folder
            # Using a simplified filename for now, yt-dlp will use video title by default
            # We can refine filename later, perhaps to include track number from Spotify.
            # For now, yt-dlp's default %(title)s.%(ext)s within track_specific_music_dir is fine.
            # So, we pass track_specific_music_dir as the 'output_path' to a generic yt_downloader.

            # Redefine download_youtube_audio to accept a full path for the output template
            # and not add "Music" itself.

            # Let's assume download_youtube_audio is a new function or download_audio is adapted.
            # For now, we'll call the existing download_audio which creates its own "Music" subfolder.
            # This means the structure will be base_output_path/Music/ (from download_audio)
            # and then our s_artist/s_album will be relative to *that* if we modify `output_template` in `download_audio`.
            # This is getting complicated.

            # Simpler: `download_audio` takes `base_output_path`.
            # `output_template` inside `download_audio` should be modified if it's a Spotify track
            # to include Artist/Album.
            # This requires passing more context to `download_audio` or `get_video_info`.

            # Let's create a new download function specific for this flow for clarity.
            download_youtube_track_for_spotify(
                youtube_video_url,
                base_output_path, # This is the root (e.g., ~/Downloads)
                s_artist,
                s_album,
                f"{str(track_number).zfill(2)} - {sanitize_filename(track_name)}", # Desired filename stem
                simulate_only
            )

    except spotipy.SpotifyException as e:
        print(f"Spotify API error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred in Spotify processing: {e}")


def download_youtube_track_for_spotify(youtube_url, base_dl_path, artist_name, album_name, track_filename_stem, simulate_only):
    """
    Downloads a specific YouTube URL, organizing it into Artist/Album folders,
    using a specific filename. This is called by the Spotify processing flow.
    """
    # base_dl_path is like ~/Downloads
    # artist_name, album_name are sanitized
    # track_filename_stem is like "01 - Track Name" (sanitized)

    # Full path for this track: base_dl_path/Music/Artist Name/Album Name/01 - Track Name.mp3
    specific_song_dir = os.path.join(base_dl_path, "Music", artist_name, album_name)
    os.makedirs(specific_song_dir, exist_ok=True)

    # Output template for yt-dlp. We want the final filename to be track_filename_stem.mp3
    # yt-dlp's -o template uses %(title)s, %(artist)s etc from the *YouTube* video.
    # We want to override the filename completely.
    # We can set the output template to a fixed name. Extension will be added by yt-dlp.
    output_template_for_yt_dlp = os.path.join(specific_song_dir, track_filename_stem + ".%(ext)s")

    if simulate_only:
        print(f"--- SIMULATING SPOTIFY->YOUTUBE DOWNLOAD ---")
        # In simulation, we don't call yt-dlp's get_video_info for the youtube_url again if we already have it.
        # Here, we just simulate the file creation at the target path.
        # The `title` for the dummy file content should ideally be from Spotify.
        # We have `track_filename_stem` which is derived from Spotify.

        # Ensure the .mp3 extension for the dummy file path
        simulated_final_path = os.path.join(specific_song_dir, track_filename_stem + ".mp3")

        try:
            with open(simulated_final_path, 'w') as f:
                f.write(f"This is a simulated audio file for '{track_filename_stem}'.\nOriginal YouTube URL: {youtube_url}\n")
            print(f"Simulated download: Created dummy file for '{track_filename_stem}' at '{simulated_final_path}'")
        except IOError as e:
            print(f"Error creating dummy file for Spotify simulation: {e}")
        return simulated_final_path # Or None if error

    else: # Actual download
        yt_dlp_command = [
            'yt-dlp',
            '-x', '--audio-format', 'mp3', '--audio-quality', '0',
            '-o', output_template_for_yt_dlp, # Use our specific path and filename stem
            '--print', 'after_move:filepath',
            '--no-simulate', '--no-playlist',
            '--no-warnings',
            youtube_url
        ]
        print(f"Attempting to download from YouTube URL (for Spotify track): {youtube_url}")
        print(f"Outputting to template: {output_template_for_yt_dlp}")
        # print(f"Command: {' '.join(yt_dlp_command)}") # Optional debug

        try:
            result = subprocess.run(yt_dlp_command, capture_output=True, text=True, encoding='utf-8', check=False)
            if result.returncode == 0:
                final_filepath = None
                for line in result.stdout.strip().split('\n'): # Get last line of stdout
                    if line.strip():
                        final_filepath = line.strip()

                if final_filepath and os.path.exists(final_filepath):
                    print(f"Successfully downloaded (for Spotify): {track_filename_stem}")
                    print(f"File saved to: {final_filepath}")
                    return final_filepath
                # ... (rest of error handling copied from download_audio)
                elif final_filepath: # yt-dlp reported path, but not found
                    print(f"yt-dlp reported path {final_filepath}, but it was not found (Spotify flow).")
                    print(f"Full yt-dlp stdout:\n{result.stdout}")
                    print(f"Full yt-dlp stderr:\n{result.stderr if result.stderr else 'Empty'}")
                    return None
                else: # No filepath from yt-dlp stdout
                    print("Could not determine downloaded file path from yt-dlp output (Spotify flow).")
                    print(f"Full yt-dlp stdout:\n{result.stdout}")
                    print(f"Full yt-dlp stderr:\n{result.stderr if result.stderr else 'Empty'}")
                    return None
            else: # yt-dlp exited with error
                print(f"Error downloading from YouTube (for Spotify track). yt-dlp stderr:")
                error_output = result.stderr.strip() if result.stderr else ""
                if not error_output and result.stdout.strip(): # if stderr is empty but stdout has info
                    error_output += f"\n(yt-dlp stdout: {result.stdout.strip()})"
                if not error_output: # if both are empty
                     error_output = f"yt-dlp exited with code {result.returncode}."

                print(error_output)
                if "HTTP Error 403" in result.stderr:
                    print("NOTE: This HTTP 403 error likely means YouTube is blocking automated requests from this IP address.")
                    print("Try again later or from a different network/machine.")
                return None
        except FileNotFoundError:
            print("Error: yt-dlp command not found. Please ensure yt-dlp is installed and in your PATH (Spotify flow).")
            return None
        except Exception as e:
            print(f"An unexpected error occurred during YouTube download (for Spotify track): {e}")
            return None
