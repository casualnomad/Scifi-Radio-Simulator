from ast import Return
import json
from TTS import backgroundsfx
import config
import random
import requests
import time
import sys
from LLM.systemprompts import jumpbridge
from TTS.texttospeech import generate_tts
from WorldState.worldstate import worldstate_load, worldstate_save, save_snapshot
from WorldState.shipgen import spawn_ship
from pydub import AudioSegment
from pydub.playback import play
import pygame
import threading
import re
import inflect

p = inflect.engine()
world = worldstate_load(config.WORLD_STATE_PATH)
story_lock = threading.Lock()
story_thread = None

# -------- Chat Call -------- #
def generate_radio_chatter():

    promptMeta = world["meta"]
    promptCurrentStoryArc = world["current_arc"]
    promptRecentTransmissions = "\n".join(world["recent_transmissions"][-3:])
    promptActiveEvents = "\n".join(world["active_events"])
    promptShipStatus = ""
    for callsign, data in world["ships"].items():
        promptShipStatus += f"{callsign}, type: {data.get('type', 'N/A')}, status: {data.get('status', 'Unknown')}, location: {data.get('location', 'Unknown')}, mood: {data.get('mood', 'Neutral')}, notes: {data.get('notes', '')}, faction: {data.get('faction', 'Unknown')}, job: {data.get('job', 'Unknown')}\n"

    promptCallsigns = ", ".join(world["ships"].keys())    
    last_transmission = world["recent_transmissions"][-1]
    last_metadata = last_transmission.split(",")[0].strip() 
    last_speaker = last_metadata.split(":")[0].strip() if ":" in last_metadata else "Unknown"
    last_shipspeaker = last_metadata.split(":")[1].strip() if ":" in last_metadata else "Unknown"
    promptgate_status = world["gate_status"]
    promptdocking_bays = world["docking_bays"]
    promptapproach_lanes = world["approach_lanes"]

    recent_speakers = [
    line.split(":")[0].strip().upper()
    for line in world["recent_transmissions"][-3:]
    ]

    # Force TOWER if it hasn't appeared in last 3
    if not any("TOWER" in s for s in recent_speakers):
        forced_role = "TOWER"
    elif not any("AI" in s for s in recent_speakers):
        forced_role = "AI"
    else:
        # Exclude recent speakers
        excluded = set(recent_speakers[-2:])
        available = {"TOWER", "AI", "CAPT"} - excluded
        forced_role = random.choice(list(available))
    
    pending = world["pending_queries"]
    pending = [q for q in world.get("pending_queries", []) if isinstance(q, dict)]
    unanswered = [q for q in pending if not q.get("answered", False)]
    if unanswered:
        pending_line = f"Unanswered query from {unanswered[0]['from']}: {unanswered[0]['query']}"
    else:
        pending_line = "No pending queries."


    system_prompt = f""" 
        You are a radio operator at a jump gate orbital structure.
        You have three characters to speak as:
            *Tower* - managing the gate and station logistics. They only talk to CAPT, ask questions, give instructions, or respond to queries. They care about all ships, but only respond to specific queries from CAPT. 
            *Capt* - Manage their own ships. Always respond with their call sign. They never give instruction about the gates or station. Only asking tower questions and responing to questions asked to their callsign. CAPT knows NOTHING about the gates or station, dont know the statuses of other capts ships.
            *AI* - This is the base AI, It is one way, no one should talk or refer to it, but it can talk to anyone else, with ONLY General Broadcasts to all ships. Keep AI messages general and not specific to one ship. They can also provide information about the gate, events, or other ships.
        Output exactly one radio transmission per prompt. Only one character per message 
        Take into account the ship types, jobs, factions and statuses, as well as the recent transmissions and active events.
        Your station has a jump gate, docking bays, and approach lanes. You are responsible for managing ship traffic and communications.
        You have the following availble: three approach lanes (lane one, lane two, lane three), two jump gates (gate one, gate two) and seven docking bays (bay one - seven).
        Docking bays and approach lanes are limited, so ships may need to wait or be redirected. Only one ship can use a docking bay at a time. Approach lanes may be clear, busy, or restricted.
        You have law enforcement authority over all ships in your jurisdiction. You can issue warnings, detain ships, or escalate to the AI for further action.
        If a ship is in distress, you can provide assistance or coordinate with the AI for rescue operations.
        If a ship is requesting docking, you can grant or deny permission based on availability and safety.
        You can also provide information about the gate, events, or other ships.
        If a ship is not answering, you can attempt to hail them or escalate to the law enforcement for further action
        You have free rein to be creative and characterful in your transmissions, but you must always stay in character as a radio operator at a jump gate orbital structure.
        If you see pirates, and they do not state their intentions, assume they are hostile and deploy any military or navy ships to take them out or scare them away. 

        Format rules:
        - Exactly one line, 6-30 words formatted like:
            TOWER: message (example: TOWER: Tower to (ship callsign), message here
            AI: message  (example: AI: AI notification here)
            CAPT format is exactly: CAPT: CALLSIGN, message -  callsign always required for identification
            Never write CAPT: CALLSIGN, message — the colon comes after the callsign, not before it.
            Do not list every gate, lane, and dock status in a single transmission — reference only what's relevant to that ship's situation.
        - No exposition, narration, or explanation
        - No ellipsis, quotes, or emojis
        - Do not let the same event dominate indefinitely. Keep it fresh and moving

        """
    
    user_prompt = f"""
        Current situation: {promptCurrentStoryArc}
        Active events: {promptActiveEvents}
        Ship status: {promptShipStatus}
        Available callsigns: {promptCallsigns}
        Pending queries: {pending_line}
        Recent transmissions:{promptRecentTransmissions}
        Station Metadata:
        gate_status: {promptgate_status}
        docking_bays: {promptdocking_bays}
        approach_lanes: {promptapproach_lanes}

        YOU MUST begin this transmission with {forced_role}. No other role is acceptable.
        Last ship speaker was {last_shipspeaker} — do not use this callsign.
        Write one transmission now.
        """

    payload = {
        "model": config.TRANSMISSION_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": config.TRANSMISSION_TEMPERATURE,
        "max_tokens": config.TRANSMISSION_MAX_TOKENS 
    }

   # Retry loop instead of recursion
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(config.LOCAL_LLAMA_SERVER_URL, json=payload, timeout=60)
            response.raise_for_status()
            
            reply = response.json()["choices"][0]["message"]["content"]  
            reply = numbers_to_words(reply)
            world["recent_transmissions"].pop(0)  # Remove the oldest transmission if you want to keep the list size manageable
            world["recent_transmissions"].append(reply)
            worldstate_save(world, config.WORLD_STATE_PATH)
            
            
            return user_prompt, reply

        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt+1}/{max_retries} failed: {e}")
            time.sleep(2)
    
    return user_prompt, "System: Comms link failure."

def generate_world_state():
    global world

    save_snapshot(world)
    story_input = dict(world)
    story_input.pop("recent_transmissions")
    recent = "\n".join(world["recent_transmissions"][-5:])
    worldpromptShipStatus = ""
    for callsign, data in world["ships"].items():
        worldpromptShipStatus += f"{callsign}, type: {data.get('type', 'N/A')}, status: {data.get('status', 'Unknown')}, location: {data.get('location', 'Unknown')}, mood: {data.get('mood', 'Neutral')}, notes: {data.get('notes', '')}, faction: {data.get('faction', 'Unknown')}, job: {data.get('job', 'Unknown')}\n"
    promptgate_status = world["gate_status"]
    promptdocking_bays = world["docking_bays"]
    promptapproach_lanes = world["approach_lanes"]

    system_prompt = """
    You manage a jump gate orbital structure. You are the narrator and world state manager.
    You track ship movements, events, crew moods, and gate systems across time.
    Take into account the ship types, jobs, factions and statuses, as well as the recent transmissions and active events.

    You may:
    - Change ship statuses
    - Evolve moods based on events
    - Resolve or escalate active events
    - Introduce new developments as the story calls for it

    Priorities:
    - Favor surprising, characterful developments over routine logistics.
    - A quiet gate is fine sometimes, but don't let realism override interest.
    - Strange, tense, or funny beats are more valuable than perfectly consistent bay math.
    - Move the story forward in time by 10 minutes per update.
    - Keep the story coherent with previous events, ship statuses, and moods.

    Rules:
    - active_events: max 6 items, one short sentence each, remove resolved events, replace escalated ones
    - Mark departed/destroyed/recovered ships with status "departed"
    - current_arc must reflect what is happening RIGHT NOW, max 20 words
    - Increment current_time by 10 minutes in valid HHMM format only (0415 + 10 = 0425)
    - Do not reference departed ships in current_arc
    - If an event has been discussed more than twice in recent_transmissions, resolve or replace it
    - Do not let the same event dominate indefinitely
    - You can change all field values but must not add or remove keys from the world state

    pending_queries rules:
    - pending_queries is a list of objects with fields: "from", "query", "answered"
    - pending_queries must have a maximum of 3 items, remove oldest if exceeded
    - When a CAPT asks a question in recent transmissions, add it with "answered": false
    - When TOWER or AI responds DIRECTLY to that callsign, set "answered": true
    - A generic broadcast does NOT count as answering a specific ship's query

    Return JSON only, no explanation, no markdown.
    """

    user_prompt = f"""
            Current world state:
            {story_input}

            Latest transmissions:
            {recent}

            All ships:
            {worldpromptShipStatus}

            Station Metadata:
            gate_status: {promptgate_status}
            docking_bays: {promptdocking_bays}
            approach_lanes: {promptapproach_lanes}

            Advance the simulation 10 minutes. Return partial JSON only:
            ships (location, status, mood, notes, faction, job) (changed ships only), active_events, current_arc, meta, gate_status, pending_queries, docking_bays, and approach_lanes. If any data is missing or unknown, try to infer it and add it. 
            Do not include recent_transmissions.
            No explanation. JSON only.
            """
    payload = {
        "model": config.STORY_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": config.STORY_TEMPERATURE,
        "max_tokens": config.STORY_MAX_TOKENS 
    }

   # Retry loop instead of recursion
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(config.LLAMA_SERVER_URL, json=payload, timeout=300)
            response.raise_for_status()
            
            reply = response.json()["choices"][0]["message"]["content"]  
            reply = reply.replace("```json", "").replace("```", "").strip()
            reply = reply.replace(": True", ": true").replace(": False", ": false")
            reply = reply[:reply.rfind("}") + 1]
            print(f"World State Update Response: {reply}")  # Debugging line

            updates = json.loads(reply)
            with story_lock:
                if "ships" in updates:
                    ships_data = updates["ships"]
                    
                    # Normalize: if the model returned a list, convert it to a dict keyed by callsign
                    if isinstance(ships_data, list):
                        ships_data = {s["callsign"]: s for s in ships_data if "callsign" in s}

                    for callsign, data in updates["ships"].items():
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

                # Work with the list (or an empty list if the key is missing).
                pending = [q for q in world.get("pending_queries", []) if isinstance(q, dict)]

                # 1️⃣ Increment the repeat counter for every pending query.
                for q in pending:
                    q["repeated"] = q.get("repeated", 0) + 1

                # 2️⃣ Identify queries that have **exceeded** the allowed repetitions.
                #    Those with `repeated >= 3` should be dropped.
                queries_to_remove = [q for q in pending if q.get("repeated", 0) >= 3]

                for rm in queries_to_remove:
                    try:
                        world["pending_queries"].remove(rm)      # list.remove() deletes the first matching dict
                        print(f"Removing [{rm['from']}] query due to timeout: {rm['query']}")
                    except ValueError:
                        # The entry was already gone – ignore safely.
                        pass
                    

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

            return user_prompt, reply

        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt+1}/{max_retries} failed: {e}")
            time.sleep(2)
    
    return user_prompt, "System: Comms link failure."


# -------- Character Selector -------- #
def choose_character(chatter):
    # Determine character based on "Name: Message" format
    if ":" in chatter:
        parts = chatter.split(":", 1)
        name_part = parts[0].strip().upper()
        message_part = parts[1].strip()
        
        # Map specific keywords to your TTS voices
        if "TOWER" in name_part or "CONTROL" in name_part:
            return "Tower", message_part
        elif "AI" in name_part or "COMPUTER" in name_part:
            return "AI", message_part
        elif "CAPT" in name_part or "COMMANDER" in name_part:
            return "Captain", message_part
        else:
            # Return the actual name found, or default if you prefer
            return "Default", message_part
    
    # Fallback if LLM didn't format correctly
    return "Default", chatter

def play_transmission(path):
    sound = pygame.mixer.Sound(path)
    transmission_channel = pygame.mixer.Channel(1)
    transmission_channel.play(sound)
    while transmission_channel.get_busy():
        time.sleep(0.1)

def numbers_to_words(text):
    def digit_by_digit(match):
        digits = match.group()
        return "-".join(p.number_to_words(d) for d in digits)
    
    # Match callsign-style numbers (3-4 digits after letters/dash)
    return re.sub(r'\d+', digit_by_digit, text)

# -------- Main Loop -------- #
def main():
    global story_thread
    print("--- Space Radio Initialized ---")

    pygame.mixer.init()
    pygame.mixer.music.load("SFX/Background.wav")
    pygame.mixer.music.set_volume(0.3)
    pygame.mixer.music.play(-1)  # -1 = loop forever
    transmission_channel = pygame.mixer.Channel(1)
    sfx_channel = pygame.mixer.Channel(2)

    backgroundsfx.start()

    try:
        while True:
            with story_lock:
             #   world["meta"]["tick"] += 1
             #   current_tick = world["meta"]["tick"]

            #if current_tick % config.TICK_UPDATE_INTERVAL == 0:
                if story_thread is None or not story_thread.is_alive():
                    print("\n--- Generating World State (background) ---")
                    story_thread = threading.Thread(
                        target=generate_world_state,
                        daemon=True
                    )
                    story_thread.start()
            prompt, chatter = generate_radio_chatter()
            
            # Skip empty responses
            if not chatter or chatter == "System: Comms link failure.":
                print("No response from comms.")
                continue

            character, trimmed_text = choose_character(chatter)

            print("\n" + "="*60)
            print(f"SPEAKER:   {character}")
            print(f"MESSAGE:   {trimmed_text}")
            print("="*60)
            
            # generate_tts is assumed to save to 'output.wav'
            try:
                generate_tts(character, trimmed_text)
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