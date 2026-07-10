import time
import random
import threading
import datetime
import os
import http.server
import functools
import json

import config
import pygame

from TTS import backgroundsfx
from TTS.texttospeech import generate_tts
from WorldState.worldstate import world, worldstate_save, story_lock, set_injection
from LLM.generateTransmission import generate_radio_chatter, generate_local_radio_chatter
from LLM.generateStory import generate_world_state, generate_local_world_state

story_thread = None


# -------- Character Selector -------- #
def choose_character(chatter):
    """Map an 'NAME: message' transmission to a TTS voice + trimmed text.
    Only three roles ever appear (TOWER, AI, CAPT) — anything that isn't
    clearly Tower or AI is treated as Capt. This also makes it robust to
    callsign-first drift (e.g. 'NVY-1140: message' instead of the correct
    'CAPT: NVY-1140, message'), which now correctly resolves to Captain
    instead of silently falling through to an unused Default voice."""
    if not chatter or ":" not in chatter:
        return "Captain", chatter or ""

    name_part, message_part = chatter.split(":", 1)
    name_part = name_part.strip().upper()
    message_part = message_part.strip()

    if name_part.startswith("TOWER") or name_part.startswith("CONTROL"):
        return "Tower", message_part
    elif name_part.startswith("AI") or name_part.startswith("COMPUTER"):
        return "AI", message_part
    else:
        return "Captain", message_part


def play_transmission(path):
    sound = pygame.mixer.Sound(path)
    transmission_channel = pygame.mixer.Channel(1)
    transmission_channel.play(sound)
    while transmission_channel.get_busy():
        time.sleep(0.1)


def start_dashboard_server():
    """Serve dashboard.html + worldstate.json over HTTP so the dashboard can
    poll it. Must run from the same folder both files live in — by default
    that's wherever config.WORLD_STATE_PATH points."""
    directory = os.path.dirname(os.path.abspath(config.WORLD_STATE_PATH)) or "."
    port = getattr(config, "DASHBOARD_PORT", 8000)

    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # suppress the per-request access log line

        def do_POST(self):
            if self.path == "/inject":
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8", errors="ignore")
                try:
                    text = json.loads(body).get("text", "").strip()
                except json.JSONDecodeError:
                    text = body.strip()

                if text:
                    set_injection(text)
                    print(f"--- Plot injection received: {text} ---")
                    self.send_response(200)
                else:
                    self.send_response(400)
                self.end_headers()
            else:
                self.send_response(404)
                self.end_headers()

    handler = functools.partial(QuietHandler, directory=directory)
    http.server.ThreadingHTTPServer.allow_reuse_address = True

    try:
        httpd = http.server.ThreadingHTTPServer(("", port), handler)
    except OSError as e:
        print(f"--- Dashboard server failed to start on port {port}: {e} ---")
        print("--- (is your old manual server still running on this port?) ---")
        return

    print(f"--- Dashboard live at http://localhost:{port}/dashboard.html (serving {directory}) ---")
    httpd.serve_forever()


# -------- Main Loop -------- #
def main():
    global story_thread
    print("--- Space Radio Initialized ---")

    if "stream_start" not in world["meta"]:
        world["meta"]["stream_start"] = datetime.datetime.utcnow().isoformat()
        worldstate_save(world, config.WORLD_STATE_PATH)

    threading.Thread(target=start_dashboard_server, daemon=True).start()

    pygame.mixer.init()
    pygame.mixer.music.load("SFX/Background.wav")
    pygame.mixer.music.set_volume(0.3)
    pygame.mixer.music.play(-1)  # loop forever

    backgroundsfx.start()

    tick = world["meta"]["tick"]
    try:
        while True:
            tick += 1

            # World state advances every TICK_UPDATE_INTERVAL loop iterations,
            # only if the previous background update has actually finished.
            if tick % config.TICK_UPDATE_INTERVAL == 0:
                with story_lock:
                    if story_thread is None or not story_thread.is_alive():
                        print("\n--- Generating World State (background) ---")
                        story_thread = threading.Thread(
                            target=generate_world_state,
                            daemon=True
                        )
                        story_thread.start()

            chatter = generate_local_radio_chatter()

            if not chatter or chatter == "System: Comms link failure.":
                print("No response from comms.")
                continue

            character, trimmed_text = choose_character(chatter)

            print("\n" + "=" * 60)
            print(f"SPEAKER:   {character}")
            print(f"MESSAGE:   {trimmed_text}")
            print("=" * 60)

            try:
                generate_tts(character, trimmed_text)  # saves to SFX/output.wav
                play_transmission("SFX/output.wav")
            except Exception as e:
                print(f"Audio Error: {e}")

            time.sleep(random.uniform(3.5, 8.5))

    except KeyboardInterrupt:
        print("\n--- Comms Terminated ---")
        if story_thread and story_thread.is_alive():
            story_thread.join(timeout=5)
        pygame.mixer.quit()


if __name__ == "__main__":
    main()
