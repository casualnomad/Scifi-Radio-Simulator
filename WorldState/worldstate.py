import datetime
import json
import os

def worldstate_load(path):
        with open(path, "r") as f:
            worldstate = json.load(f)
            return worldstate
    
def worldstate_save(worldstate, path):
        with open(path, "w") as f:
            json.dump(worldstate, f, indent=4)

def save_snapshot(world):
    os.makedirs("snapshots", exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"snapshots/worldstate_{timestamp}.json"
    with open(path, "w") as f:
        json.dump(world, f, indent=4)