# main_player.py
# Main application script for the GUI Music Player.
# Will use Tkinter for the GUI and coordinate other modules.

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import database_manager
import library_scanner
import audio_player # Assuming audio_player.py handles pygame initialization

class MusicPlayerApp:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("Python Music Player")
        self.root.geometry("900x650")

        self.db_manager = database_manager # Alias for convenience
        self.db_manager.create_tables() # Ensure tables exist

        self.player = audio_player.AudioPlayer()

        self.current_library_path = library_scanner.get_music_library_path()
        # TODO: Allow user to set/change library path via GUI

        self.setup_ui()
        self.load_tracks_to_listbox()

    def setup_ui(self):
        # --- Menu ---
        menubar = tk.Menu(self.root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Scan Music Library", command=self.scan_library)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=filemenu)
        self.root.config(menu=menubar)

        # --- Main Panes ---
        main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left Pane (Navigation - Placeholder for now)
        left_frame = ttk.Frame(main_pane, width=200, height=400, relief=tk.SUNKEN)
        # TODO: Add Treeview for Artists/Albums/Playlists
        nav_label = ttk.Label(left_frame, text="Navigation (Artists/Albums)")
        nav_label.pack(padx=5, pady=5)
        main_pane.add(left_frame, weight=1)

        # Right Pane (Track List and Controls)
        right_container_frame = ttk.Frame(main_pane) # Container for track list and controls below it
        main_pane.add(right_container_frame, weight=4)

        # Track List (Treeview)
        self.track_list_frame = ttk.Frame(right_container_frame)
        self.track_list_frame.pack(fill=tk.BOTH, expand=True)

        columns = ('#0', 'Title', 'Artist', 'Album', 'Duration') # #0 is for the tree column
        self.track_tree = ttk.Treeview(self.track_list_frame, columns=columns[1:], show='headings', selectmode="browse")

        self.track_tree.heading('Title', text='Title')
        self.track_tree.column('Title', width=250)
        self.track_tree.heading('Artist', text='Artist')
        self.track_tree.column('Artist', width=150)
        self.track_tree.heading('Album', text='Album')
        self.track_tree.column('Album', width=150)
        self.track_tree.heading('Duration', text='Time')
        self.track_tree.column('Duration', width=60, anchor=tk.E)

        # Scrollbar
        scrollbar = ttk.Scrollbar(self.track_list_frame, orient=tk.VERTICAL, command=self.track_tree.yview)
        self.track_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.track_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.track_tree.bind("<Double-1>", self.on_track_double_click)

        # --- Playback Controls Frame ---
        controls_frame = ttk.Frame(right_container_frame)
        controls_frame.pack(fill=tk.X, pady=10)

        self.play_pause_button = ttk.Button(controls_frame, text="Play", command=self.toggle_play_pause)
        self.play_pause_button.pack(side=tk.LEFT, padx=5)

        stop_button = ttk.Button(controls_frame, text="Stop", command=self.player.stop_song)
        stop_button.pack(side=tk.LEFT, padx=5)

        # TODO: Prev/Next buttons, progress bar, volume slider

    def format_duration(self, seconds_float):
        if seconds_float is None: return "0:00"
        seconds = int(seconds_float)
        minutes = seconds // 60
        seconds %= 60
        return f"{minutes}:{seconds:02d}"

    def load_tracks_to_listbox(self, tracks_data=None):
        # Clear existing items
        for item in self.track_tree.get_children():
            self.track_tree.delete(item)

        if tracks_data is None:
            tracks_data = self.db_manager.get_all_tracks() # Default sort

        for track_row in tracks_data:
            # track_row is a sqlite3.Row object (dictionary-like)
            duration_str = self.format_duration(track_row['duration'])
            # Store filepath in the item itself using 'values' for hidden data or a custom attribute
            # For Treeview, we can use the item ID (iid) to store the filepath or track_id
            # Or, more simply, store track_id from DB as first value, then hide that column.
            # Here, we'll store filepath implicitly by track_id which we'll use to fetch it.
            self.track_tree.insert('', tk.END, iid=track_row['id'], values=(
                track_row['title'] or "Unknown Title",
                track_row['artist'] or "Unknown Artist",
                track_row['album'] or "Unknown Album",
                duration_str
            ))

    def scan_library(self):
        if not self.current_library_path:
            messagebox.showerror("Error", "Music library path not set or found.")
            # TODO: Add a dialog to select library path
            return

        # Ask for confirmation or run in background (for large libraries)
        if messagebox.askyesno("Scan Library", f"Scan '{self.current_library_path}' for music?\nThis may take a while for large libraries."):
            # For now, run synchronously. Consider threading for actual app.
            library_scanner.scan_and_populate_library(self.current_library_path)
            messagebox.showinfo("Scan Complete", "Music library scan finished.")
            self.load_tracks_to_listbox() # Refresh the list

    def on_track_double_click(self, event):
        selected_item_iid = self.track_tree.focus() # Get focused item's IID
        if not selected_item_iid:
            return

        # The IID is the track_id from the database
        track_id = int(selected_item_iid)
        track_data_tuple = self.db_manager.get_track_by_id(track_id) # returns a tuple

        if track_data_tuple:
            # Convert tuple to a dictionary-like object or access by index
            # Assuming get_track_by_id returns a tuple: (id, filepath, title, ...)
            filepath_index = 1 # Index of filepath in the tuple from get_track_by_id
            filepath = track_data_tuple[filepath_index]

            print(f"Double-clicked track ID: {track_id}, filepath: {filepath}")
            if self.player.load_song(filepath):
                self.player.play_song()
                self.play_pause_button.config(text="Pause")
            else:
                messagebox.showerror("Playback Error", f"Could not load or play song: {filepath}")
        else:
            messagebox.showerror("Error", f"Could not find track data for ID: {track_id}")

    def toggle_play_pause(self):
        if not self.player.current_song_path: # No song loaded
            # Try to play the selected song in the list if any
            selected_item_iid = self.track_tree.focus()
            if selected_item_iid:
                self.on_track_double_click(None) # Simulate double click
            return

        if self.player.playing and not self.player.paused:
            self.player.pause_song()
            self.play_pause_button.config(text="Play")
        elif self.player.playing and self.player.paused:
            self.player.unpause_song()
            self.play_pause_button.config(text="Pause")
        else: # Not playing (stopped or never started)
            self.player.play_song() # Assumes song is loaded
            self.play_pause_button.config(text="Pause")


if __name__ == "__main__":
    if audio_player.pygame is None:
        messagebox.showerror("Dependency Error", "Pygame not found. Please install it to run the music player.")
    else:
        root = tk.Tk()
        app = MusicPlayerApp(root)
        root.mainloop()
