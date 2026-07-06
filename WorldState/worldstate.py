import datetime
import json
import os
import threading

import config


def worldstate_load(path):
    with open(path, "r") as f:
        return json.load(f)


def worldstate_save(worldstate, path):
    with open(path, "w") as f:
        json.dump(worldstate, f, indent=4)


def save_snapshot(world):
    os.makedirs("snapshots", exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"snapshots/worldstate_{timestamp}.json"
    with open(path, "w") as f:
        json.dump(world, f, indent=4)


# Single shared world state + lock. main.py, generateStory.py, and
# generateTransmission.py all import `world` from here instead of each
# loading their own copy, so a mutation in one module is visible to the others.
world = worldstate_load(config.WORLD_STATE_PATH)
story_lock = threading.Lock()
