# audio_player.py
# Handles audio playback using pygame.mixer.
# Functions for loading, playing, pausing, stopping, volume control, etc.

try:
    import pygame
except ImportError:
    print("Pygame library not found. Please install it with 'pip install pygame'")
    pygame = None

class AudioPlayer:
    def __init__(self):
        if pygame:
            pygame.mixer.init()
            print("Pygame mixer initialized.")
        else:
            print("AudioPlayer cannot function without pygame.")
        self.current_song_path = None
        self.playing = False
        self.paused = False

    def load_song(self, song_path):
        if not pygame or not pygame.mixer.get_init():
            print("Error: Pygame mixer not initialized.")
            return False
        try:
            pygame.mixer.music.load(song_path)
            self.current_song_path = song_path
            print(f"Loaded song: {song_path}")
            return True
        except pygame.error as e:
            print(f"Error loading song {song_path}: {e}")
            self.current_song_path = None
            return False

    def play_song(self):
        if not pygame or not pygame.mixer.get_init() or not self.current_song_path:
            print("Error: No song loaded or mixer not initialized.")
            return
        if not self.playing or self.paused:
            pygame.mixer.music.play()
            self.playing = True
            self.paused = False
            print(f"Playing: {self.current_song_path}")

    def pause_song(self):
        if not pygame or not pygame.mixer.get_init(): return
        if self.playing and not self.paused:
            pygame.mixer.music.pause()
            self.paused = True
            print("Playback paused.")

    def unpause_song(self):
        if not pygame or not pygame.mixer.get_init(): return
        if self.playing and self.paused:
            pygame.mixer.music.unpause()
            self.paused = False
            print("Playback resumed.")

    def stop_song(self):
        if not pygame or not pygame.mixer.get_init(): return
        pygame.mixer.music.stop()
        self.playing = False
        self.paused = False
        self.current_song_path = None # Or perhaps just set position to 0 and pause? For now, stop means unload.
        print("Playback stopped.")

    def set_volume(self, volume_level): # volume_level between 0.0 and 1.0
        if not pygame or not pygame.mixer.get_init(): return
        clamped_volume = max(0.0, min(1.0, volume_level))
        pygame.mixer.music.set_volume(clamped_volume)
        print(f"Volume set to {clamped_volume*100:.0f}%")

    def get_busy(self): # Checks if music is currently playing (or paused)
        if not pygame or not pygame.mixer.get_init(): return False
        return pygame.mixer.music.get_busy()

    def get_pos(self): # Returns playback position in milliseconds
        if not pygame or not pygame.mixer.get_init(): return -1
        return pygame.mixer.music.get_pos()

    # TODO: Add handling for end-of-song events for playlists/queue

if __name__ == "__main__":
    if pygame:
        player = AudioPlayer()
        # This is a placeholder for actual testing with an audio file.
        # You would need an MP3 file named "test.mp3" in the same directory.
        # if player.load_song("test.mp3"):
        #     player.play_song()
        #     input("Playing test.mp3. Press Enter to stop...") # Keep script alive
        #     player.stop_song()
        print("Audio Player - Basic structure (Not yet fully implemented for GUI integration)")
    else:
        print("Pygame not available, AudioPlayer functionality limited.")
