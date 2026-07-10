import config
import requests
import json
import time
import apikey
from WorldState.worldstate import world, worldstate_save, save_snapshot, story_lock, pop_injection
from WorldState.shipgen import spawn_ship
from LLM.promptutils import ship_lines, compact

world_system_prompt = """You are the narrator and world-state manager for a jump gate orbital structure. Track ship movements, events, moods, and gate systems over time, accounting for ship types, jobs, factions, statuses, recent transmissions, and active events.

You may change ship statuses, evolve moods, resolve/escalate events, and introduce new developments.

Priorities: favor surprising, characterful developments over routine logistics. Strange, tense, or funny beats beat perfectly consistent bay math. Advance time by 10 minutes per update. Stay coherent with prior events/statuses/moods.

Rules:
- active_events: max 6, one short sentence each; drop resolved, replace escalated, don't let one dominate; resolve/replace anything discussed 3+ times in recent transmissions
- current_arc: max 20 words, reflects what's happening RIGHT NOW, never references departed ships
- Mark departed/destroyed/recovered ships with status "departed"
- current_time: increment by 10 min, valid HHMM (e.g. 0415 -> 0425)
- Do not add or remove world-state keys, only change values

pending_queries: list of {"from", "query", "answered"}, max 3, oldest dropped first. Add when CAPT asks TOWER/AI a question ("answered": false). Set true only when TOWER/AI replies DIRECTLY to that callsign — a general broadcast doesn't count.

Return JSON only, no markdown, no explanation. ship notes: MAX 120 characters per ship. 
Lane status must be exactly ONE of: available, occupied, vacant, impassable, hazard, restricted, incoming
Gate status must be exactly ONE of: vacant, occupied, hold, lockdown, failure
Bay status must be exactly ONE of: available, occupied, docking, undocking, compromised, collapsed, destroyed
Match this structure — this is a real example. Only return fields that have changed or updated:
{"ships": {"NVY-1140": {"location": "sector one", "status": "patrolling", "mood": "alert", notes: MAX 120 characters, remove if needed", "faction": "Navy", "job": "Law Enforcement"}}, "active_events": ["A quiet morning shift continues at the gate."], "current_arc": "Routine operations continue at the gate.", "meta": {"tick": 0, "current_time": "0610"}, "gate_status": {"gate_a": "vacant", "gate_b": "vacant"}, "docking_bays": {"Bay 1": "vacant", "Bay 2": "occupied", "Bay 3": "vacant", "Bay 4": "occupied", "Bay 5": "vacant", "Bay 6": "occupied"}, "approach_lanes": {"Lane 1": "available", "Lane 2": "vacant"}, "pending_queries": [{"from": "NVY-1140", "query": "Requesting docking clearance", "answered": false}]}"""


def build_world_prompt():
    """Build the user prompt fresh from current world state — must be called every
    generation, not once at import, or the model just sees the same input each tick."""
    ships = ship_lines(world["ships"])
    station = (
        f"gates[{compact(world['gate_status'])}] "
        f"docks[{compact(world['docking_bays'])}] "
        f"lanes[{compact(world['approach_lanes'])}]"
    )
    active_events = "\n".join(f"- {e}" for e in world["active_events"])
    recent = "\n".join(world["recent_transmissions"][-5:])

    injection = pop_injection()
    director_note = (
        f"\nDirector's note: {injection}\nWork this into the story naturally, over this update or the next couple.\n"
        if injection else ""
    )

    return f"""Ships:
{ships}

Station: {station}

Current arc: {world['current_arc']}

Active events:
{active_events}

Pending queries: {world['pending_queries'] or 'None'}

Meta: tick={world['meta']['tick']}, time={world['meta']['current_time']}

Recent transmissions:
{recent}
{director_note}
Advance the simulation 10 minutes. Return JSON only."""


def generate_world_state():
    global world

    save_snapshot(world)
    user_prompt = build_world_prompt()

    payload = {
        "model": config.API_STORY_MODEL,
        "max_tokens": 2024,
        "system": [
            {
                "type": "text",
                "text": world_system_prompt,
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
            
            print(response)
            response.raise_for_status()
            res_json = response.json()
            # Find the text block dynamically, ignoring thinking blocks
            reply = None
            for block in res_json.get("content", []):
                if block.get("type") == "thinking":
                    print(block.get("text"))
                if block.get("type") == "text":
                    reply = block.get("text")
                    break
            
            if reply is None:
                print("Warning: Model hit max_tokens during its thinking phase and never generated text!")
                return "System: Comms static (Thinking timeout)."    
            reply = reply.replace("```json", "").replace("```", "").strip()
            reply = reply.replace(": True", ": true").replace(": False", ": false")
            reply = reply[:reply.rfind("}") + 1]

            updates = json.loads(reply)  # bad JSON raises here -> caught below -> retried
            ingest_world_state(updates)
            print(f"World State Update Response: {reply}")
            return user_prompt, reply

        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt+1}/{max_retries} failed (network): {e}")
            time.sleep(2)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Attempt {attempt+1}/{max_retries} failed (bad JSON): {e}")
            time.sleep(2)

    print("World state update failed after retries — keeping previous state.")
    return user_prompt, "System: Comms link failure."

def generate_local_world_state():
    global world

    save_snapshot(world)
    user_prompt = build_world_prompt()

    payload = {
        "model": config.STORY_MODEL,
        "messages": [
            {"role": "system", "content": world_system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": config.STORY_TEMPERATURE,
        "max_tokens": config.STORY_MAX_TOKENS
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(config.LLAMA_SERVER_URL, json=payload, timeout=60)
            response.raise_for_status()

            reply = response.json()["choices"][0]["message"]["content"]
            reply = reply.replace("```json", "").replace("```", "").strip()
            reply = reply.replace(": True", ": true").replace(": False", ": false")
            reply = reply[:reply.rfind("}") + 1]

            updates = json.loads(reply)  # bad JSON raises here -> caught below -> retried
            ingest_world_state(updates)
            print(f"World State Update Response: {reply}")
            return user_prompt, reply

        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt+1}/{max_retries} failed (network): {e}")
            time.sleep(2)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Attempt {attempt+1}/{max_retries} failed (bad JSON): {e}")
            time.sleep(2)

    print("World state update failed after retries — keeping previous state.")
    return user_prompt, "System: Comms link failure."


def ingest_world_state(updates):
    global world
    with story_lock:
        if "ships" in updates:
            ships_data = updates["ships"]

            # Normalize: if the model returned a list, convert it to a dict keyed by callsign
            if isinstance(ships_data, list):
                ships_data = {s["callsign"]: s for s in ships_data if "callsign" in s}

            for callsign, data in ships_data.items():
                if not isinstance(data, dict):
                    print(f"Skipping malformed update for {callsign}: expected dict, got {type(data).__name__} -> {data!r}")
                    continue
                if callsign in world["ships"]:
                    world["ships"][callsign].update(data)
                else:
                    world["ships"][callsign] = data

        if "active_events" in updates:
            world["active_events"] = updates["active_events"]

        if "current_arc" in updates:
            world["current_arc"] = updates["current_arc"]

        if "meta" in updates:
            world["meta"].update(updates["meta"])

        if "gate_status" in updates:
            world["gate_status"].update(updates["gate_status"])

        if "docking_bays" in updates:
            world["docking_bays"].update(updates["docking_bays"])

        if "approach_lanes" in updates:
            world["approach_lanes"].update(updates["approach_lanes"])

        if "pending_queries" in updates:
            world["pending_queries"] = [
                q for q in updates["pending_queries"]
                if not q.get("answered", False)
            ]

        pending = [q for q in world.get("pending_queries", []) if isinstance(q, dict)]

        # Increment the repeat counter for every pending query
        for q in pending:
            q["repeated"] = q.get("repeated", 0) + 1

        # Drop queries that have gone unanswered too many ticks in a row
        queries_to_remove = [q for q in pending if q.get("repeated", 0) >= 3]
        for rm in queries_to_remove:
            try:
                world["pending_queries"].remove(rm)
                print(f"Removing [{rm['from']}] query due to timeout: {rm['query']}")
            except ValueError:
                pass  # already gone, ignore

        to_remove = [
            callsign for callsign, data in world["ships"].items()
            if data.get("status") in ("departed", "destroyed", "recovered", "fled", "escaped")
        ]

        for callsign in to_remove:
            print(f"Removing ship {callsign} due to status: {world['ships'][callsign]['status']}")
            del world["ships"][callsign]
            newship = spawn_ship()
            added_callsign = newship["callsign"]
            world["ships"][added_callsign] = newship
            print(f"Added new ship {added_callsign} of type {newship['type']} with status {newship['status']}")

        world["meta"]["tick"] = 0
        worldstate_save(world, config.WORLD_STATE_PATH)

    print("--- World State Updated ---")
