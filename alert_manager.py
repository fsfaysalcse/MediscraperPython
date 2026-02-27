
import threading
import time
import os
import subprocess
try:
    from playsound import playsound
except ImportError:
    playsound = None

class AlertManager:
    def __init__(self, sound_file="beep.mp3"):
        self.sound_file = os.path.abspath(sound_file) # Absolute path is safer
        self.is_playing = False
        self.thread = None

    def _play_loop(self):
        """Internal loop to play sound continuously while is_playing is True."""
        print(f"DEBUG: Starting Alert Loop. File: {self.sound_file}")
        
        while self.is_playing:
            played = False
            try:
                # Method 1: playsound library (Cross Platform)
                if playsound:
                    # playsound 1.2.2 block param is default True, which is good for us
                    playsound(self.sound_file)
                    played = True
            except Exception as e:
                # print(f"DEBUG: playsound failed: {e}")
                pass
            
            if not played:
                try:
                    # Method 2: macOS Native
                    subprocess.run(["afplay", self.sound_file], check=False)
                    played = True
                except:
                    pass

            if not played:
                # Method 3: Terminal Bell (Fallback)
                print('\a')
                time.sleep(1)
            
            # Small delay if the method was non-blocking or very short
            if self.is_playing:
                time.sleep(0.5)

    def start(self):
        """Starts the alert sound in a background thread."""
        if not self.is_playing:
            self.is_playing = True
            self.thread = threading.Thread(target=self._play_loop, daemon=True)
            self.thread.start()

    def stop(self):
        """Stops the alert sound."""
        print("DEBUG: Stopping Alert Loop.")
        self.is_playing = False
        if self.thread:
            self.thread.join(timeout=1)
            self.thread = None
