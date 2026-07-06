import config
import requests
import json
import time
import apikey
import random

from WorldState.worldstate import world, worldstate_save
from LLM.promptutils import numbers_to_words, ship_lines, compact

transmission_system_prompt = """You are a radio operator at a jump gate orbital structure, voicing three characters:

TOWER — manages the gate and station. Only talks to CAPT: asks questions, gives instructions, responds to queries. Cares about all ships but only directly addresses CAPT queries.
CAPT — commands their own ship, always self-identifies by callsign. Never discusses gates/station/other ships' statuses. Only asks Tower questions or answers questions addressed to their callsign.
AI — one-way general broadcasts only, never addressed or replied to. Keeps messages station-wide, not ship-specific. Can reference gate/event/ship info.

You manage: 3 approach lanes, 2 jump gates, 7 docking bays. One ship per bay. Lanes may be clear, busy, or restricted. You have law enforcement authority — warn, detain, or escalate to AI. Assist ships in distress. Grant/deny docking based on availability. If pirates don't state intentions, assume hostile and deploy military/navy to intercept or deter.
CAPT never says "this is Tower" or "this is AI" — CAPT only ever identifies as their own callsign.

Output exactly ONE transmission, one character, 6-30 words:
TOWER: message (e.g. "TOWER: Tower to <callsign>, message")
AI: message
CALLSIGN: message 

No exposition, ellipses, quotes, or emojis. Reference only what's relevant to the ship's situation — don't recite every gate/lane/dock status. Don't let one event dominate indefinitely; keep it moving."""


def build_transmission_prompt():
    """Build the user prompt fresh from current world state. Must be called every
    generation — building it once at import time is what caused identical repeated
    transmissions, since the model was seeing the exact same prompt every call."""
    current_arc = world["current_arc"]
    active_events = "\n".join(f"- {e}" for e in world["active_events"])
    ships = ship_lines(world["ships"])
    station = (
        f"gates[{compact(world['gate_status'])}] "
        f"docks[{compact(world['docking_bays'])}] "
        f"lanes[{compact(world['approach_lanes'])}]"
    )
    recent = "\n".join(world["recent_transmissions"][-5:])

    recent_speakers = [
        line.split(":")[0].strip().upper()
        for line in world["recent_transmissions"][-3:]
    ]

    # Force TOWER if it hasn't appeared in last 3, then AI, otherwise pick from what's left
    if not any("TOWER" in s for s in recent_speakers):
        forced_role = "TOWER"
    elif not any("AI" in s for s in recent_speakers):
        forced_role = "AI"
    else:
        excluded = set(recent_speakers[-2:])
        available = {"TOWER", "AI", "CAPT"} - excluded
        forced_role = random.choice(list(available)) if available else "TOWER"

    last_transmission = world["recent_transmissions"][-1]
    last_metadata = last_transmission.split(",")[0].strip()
    last_shipspeaker = last_metadata.split(":")[1].strip() if ":" in last_metadata else "Unknown"

    pending = [q for q in world.get("pending_queries", []) if isinstance(q, dict)]
    unanswered = [q for q in pending if not q.get("answered", False)]
    pending_line = (
        f"Unanswered query from {unanswered[0]['from']}: {unanswered[0]['query']}"
        if unanswered else "No pending queries."
    )

    user_prompt = f"""Situation: {current_arc}

Active events:
{active_events}

Ships:
{ships}

Station: {station}

Pending: {pending_line}

Recent transmissions:
{recent}

Begin with {forced_role}. Do not use callsign {last_shipspeaker} (last speaker). Write one transmission now."""

    return user_prompt


def generate_radio_chatter():
    global world

    user_prompt = build_transmission_prompt()

    payload = {
        "model": config.API_STORY_MODEL,
        "max_tokens": 1024,
        "thinking": {
            "type": "disabled" 
            },
        "system": [
            {
                "type": "text",
                "text": transmission_system_prompt,
                "cache_control": {"type": "ephemeral"}
            }
        ],
        "messages": [
            {"role": "user", "content": user_prompt}
        ]
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": apikey.APIkey, "anthropic-version": "2023-06-01"},
            json=payload
            )            
            
            response.raise_for_status()
            res_json = response.json()
            # Find the text block dynamically, ignoring thinking blocks
            reply = None
            for block in res_json.get("content", []):
                if block.get("type") == "text":
                    reply = block.get("text")
                    break
            
            if reply is None:
                print("Warning: Model hit max_tokens during its thinking phase and never generated text!")
                return "System: Comms static (Thinking timeout)."    
            return ingest_radio_chatter(reply)

        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt+1}/{max_retries} failed: {e}")
            time.sleep(2)

    return "System: Comms link failure."


def generate_local_radio_chatter():
    global world

    user_prompt = build_transmission_prompt()

    payload = {
        "model": config.TRANSMISSION_MODEL,
        "messages": [
            {"role": "system", "content": transmission_system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": config.TRANSMISSION_TEMPERATURE,
        "max_tokens": config.TRANSMISSION_MAX_TOKENS
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(config.LLAMA_SERVER_URL, json=payload, timeout=60)
            response.raise_for_status()
            reply = response.json()["choices"][0]["message"]["content"]
            return ingest_radio_chatter(reply)

        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt+1}/{max_retries} failed: {e}")
            time.sleep(2)

    return "System: Comms link failure."


def ingest_radio_chatter(reply):
    world["recent_transmissions"].pop(0)  # keep the list size manageable
    world["recent_transmissions"].append(reply)
    world["meta"]["total_transmissions"] = world["meta"].get("total_transmissions", 0) + 1
    world["meta"]["tick"] = world["meta"]["tick"] +1
    worldstate_save(world, config.WORLD_STATE_PATH)
    return reply
