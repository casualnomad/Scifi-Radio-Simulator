import random

SHIP_TYPES = {
    "ORE": "Mining Barge",
    "HFT": "Heavy Freighter",
    "LFT": "Light Freighter",
    "GFT": "Gas Freighter",
    "ESC": "Escort Corvette",
    "FRG": "Frigate",
    "DSTR": "Destroyer",
    "PAT": "Patrol Ship",
    "SHU": "Shuttle",
    "TNK": "Tanker",
    "COU": "Courier",
    "SAL": "Salvage Tug",
    "REF": "Repair Tender",
    "SCI": "Science Vessel",
    "NVY": "Navy Ship",
    "HAU": "Hauler"
}

FACTIONS = [
    "Alliance",
    "Independent",
    "Pirates",
    "Merchant Guild",
    "Navy",
    "Explorers' League",
    "Mining Consortium",
    "Corporate Security",
    "Religious Order",
    "Free Colonies"
]

JOBS = [
    "Miner",
    "Ore hauler",
    "Fuel runner",
    "Cargo courier",
    "Smuggler",
    "Salvager",
    "Patrol pilot",
    "Escort captain",
    "Bounty hunter",
    "System scout",
    "Deep-space explorer",
    "Salvage engineer",
    "Station trader",
    "Naval contractor",
    "Pirate raider",
    "Diplomatic envoy",
    "Shipbreaker",
    "Xenotech researcher"
]

JOB_CARGO = {
    "Miner": ["ore", "raw minerals", "rock samples"],
    "Ore hauler": ["ore", "refined metal"],
    "Fuel runner": ["reactive fuel", "deuterium", "hydrogen canisters"],
    "Cargo courier": ["sealed parcels", "documents", "high-value cargo"],
    "Smuggler": ["contraband", "black market goods", "unregistered tech"],
    "Salvager": ["scrap metal", "wreck parts", "salvage crates"],
    "Patrol pilot": ["none", "inspection kits", "security supplies"],
    "Escort captain": ["none", "ammo", "rations"],
    "Bounty hunter": ["detained target", "evidence", "weapons"],
    "System scout": ["sensor data", "nav charts", "probe logs"],
    "Deep-space explorer": ["survey data", "artifacts", "samples"],
    "Salvage engineer": ["spare parts", "repair kits", "field tools"],
    "Station trader": ["consumer goods", "trade stock", "electronics"],
    "Naval contractor": ["military supplies", "spare reactors", "munitions"],
    "Pirate raider": ["stolen cargo", "weapons", "booty"],
    "Diplomatic envoy": ["sealed diplomatic crates", "gift cargo", "protocol items"],
    "Shipbreaker": ["scrap", "waste metal", "hazardous parts"],
    "Xenotech researcher": ["alien artifacts", "sealed specimens", "lab containers"]
}

CARGO_FLAGS = {
    "legal": ["ore", "raw minerals", "refined metal", "scrap metal", "spare parts"],
    "restricted": ["reactive fuel", "high-value cargo", "weapons", "munitions", "alien artifacts"],
    "illegal": ["contraband", "black market goods", "unregistered tech", "stolen cargo"],
    "hazardous": ["deuterium", "hydrogen canisters", "hazardous parts", "sealed specimens"]
}


import random

def get_ship_type_for_job(job):
    if job in ["Miner", "Ore hauler"]:
        return "ORE"
    elif job == "Fuel runner":
        return "TNK"
    elif job in ["Cargo courier", "Station trader"]:
        return "COU"
    elif job == "Smuggler":
        return "LFT"
    elif job in ["Salvager", "Shipbreaker"]:
        return "SAL"
    elif job in ["Patrol pilot", "Escort captain", "Bounty hunter", "Naval contractor"]:
        return "ESC"
    elif job in ["System scout", "Deep-space explorer", "Xenotech researcher"]:
        return "SCI"
    elif job == "Salvage engineer":
        return "REF"
    elif job == "Pirate raider":
        return "FRG"
    elif job == "Diplomatic envoy":
        return "SHU"
    else:
        return "HAU"

def get_cargo_flag(cargo):
    for flag, items in CARGO_FLAGS.items():
        if cargo in items:
            return flag
    return "legal"

def spawn_ship():
    job = random.choice(JOBS)
    ship_code = get_ship_type_for_job(job)
    number = random.randint(100, 9999)
    cargo = random.choice(JOB_CARGO[job])

    return {
        "callsign": f"{ship_code}-{number}",
        "type": SHIP_TYPES[ship_code],
        "location": "",
        "status": "",
        "cargo": cargo,
        "cargo_flagged": get_cargo_flag(cargo),
        "faction": random.choice(FACTIONS),
        "job": job,
        "mood": "neutral",
        "notes": ""
    }
