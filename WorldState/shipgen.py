import random

SHIP_TYPES = {
    "ORE": "Mining Barge",
    "HFT": "Heavy Freighter",
    "GFT": "Gas Freighter",
    "ESC": "Escort",
    "SHU": "Shuttle",
    "TNK": "Tanker",
    "COU": "Courier",
    "NVY": "Navy Ship",
    "HAU": "Hauler"
}

def spawn_ship():
    shiptype = random.choice(list(SHIP_TYPES.keys()))
    number = random.randint(100, 9999)
    flagged = random.choice([True, False])
    return {
        "callsign": f"{shiptype}-{number}",
        "type": SHIP_TYPES[shiptype],
        "location": "",
        "status": "inbound",
        "cargo_flagged": flagged,
        "mood": "neutral",
        "notes": ""
    }

