# backgroundsfx.py
import os
import random
import threading
import time
import pygame

# ------------------------------------------------------------------ #
AUDIO_ROOT = "SFX/noises/"             # folder that holds all radio clips
SUPPORTED = {".wav", ".ogg", ".mp3"}   # extensions you accept
MIN_DELAY = 60                        # seconds
MAX_DELAY = 120
# ------------------------------------------------------------------ #

def _load_file_list():
    """Return absolute paths for every supported file in AUDIO_ROOT."""
    return [os.path.join(AUDIO_ROOT, f)
            for f in os.listdir(AUDIO_ROOT)
            if os.path.splitext(f)[1].lower() in SUPPORTED]

# Global mutable list – can be refreshed later if you add files at runtime
audio_files = _load_file_list()


def _wait_until_idle(ch):
    while ch.get_busy():
        time.sleep(0.1)


def play_sfx(path, volume):
    """Play the supplied file on Channel 2."""
    sound = pygame.mixer.Sound(path)
    sfx_channel = pygame.mixer.Channel(2)
    sfx_channel.set_volume(volume)
    sfx_channel.play(sound)
    _wait_until_idle(sfx_channel)


def _schedule_next():
    delay = random.uniform(MIN_DELAY, MAX_DELAY)
    threading.Timer(delay, _play_random).start()


def _play_random():
    """Select a random clip and hand it to Channel 2."""
    volume = random.uniform(0.1, 0.2)  # random volume for variety
    if not audio_files:
        print("⚠️ backgroundsfx: No audio files found in", AUDIO_ROOT)
        return
    path = random.choice(audio_files)
    print(f"🔊 backgroundsfx → {os.path.basename(path)} at {volume}")
    play_sfx(path, volume)
    _schedule_next()


def start():
    """
    Initialise pygame’s mixer (if not already initialised) and fire the
    first random SFX after a short warm‑up.
    """
    if not pygame.mixer.get_init():
        pygame.mixer.init()
    # give the main script a moment to load its background music first
    threading.Timer(5, _play_random).start()


def refresh_file_list():
    """Call this from main.py if you drop new clips into SFX/ while running."""
    global audio_files
    audio_files = _load_file_list()
