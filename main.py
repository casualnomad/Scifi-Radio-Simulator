
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

# -------- World Generation -------- #
promptMeta = world["meta"]
promptCurrentStoryArc = world["current_arc"]
promptRecentTransmissions = "\n".join(world["recent_transmissions"][-3:])
promptActiveEvents = "\n".join(world["active_events"])
promptShipStatus = ""
for callsign, data in world["ships"].items():
    promptShipStatus += f"{callsign}, type: {data['type']}, status: {data['status']}, location: {data['location']}, mood: {data['mood']}, notes: {data['notes']}\n"

# -------- Chat Call -------- #
def generate_radio_chatter():
    promptCallsigns = ", ".join(world["ships"].keys())    
    last_transmission = world["recent_transmissions"][-1]
    last_metadata = last_transmission.split(",")[0].strip() 
    last_speaker = last_metadata.split(":")[0].strip() if ":" in last_metadata else "Unknown"
    last_shipspeaker = last_metadata.split(":")[1].strip() if ":" in last_metadata else "Unknown"


    system_prompt = f""" 
        -ONLY EVER OUTPUT ONE COMMUNICATION
        - Output exactly one line per prompt, 6–20 words, with role tag (CAPT, TOWER, AI)
        - No exposition, no narration, do not repeat previous line structures
        - Never repeat the same speaker twice in a row
        - Rotate between AI, TOWER, and CAPT each transmission
        - CAPT lines must always include the ship callsign after CAPT. Format example: CAPT: Callsign, message
        - Never write CAPT: message without a callsign.
        - Never address the same callsign consecutively
        """
    user_prompt = f"""
        Current story arc: {promptCurrentStoryArc}
        Active events: {promptActiveEvents}
        Recent transmissions: {promptRecentTransmissions}
        Ship status: {promptShipStatus}
        Last speaker was {last_speaker}. Do not repeat the same speaker.
        Last ship speaker was {last_shipspeaker}. Do not repeat the same ship speaker.
        ONLY use these callsigns: {promptCallsigns}
        Any other callsign does not exist. Do not invent or reuse departed ships.
        Write one transmission. Format: SPEAKER: message. 6-20 words.
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
            response = requests.post(config.LLAMA_SERVER_URL, json=payload, timeout=60)
            response.raise_for_status()
            
            reply = response.json()["choices"][0]["message"]["content"]  
            reply = numbers_to_words(reply)
            (world)
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

    system_prompt = f""" 
        You manage a jump gate orbital structure. You are the narrator and world 
        state manager, not a radio operator. You track ship movements, ongoing 
        events, crew moods, and gate systems across time.

        When given a world state JSON, advance the simulation forward by 
        approximately 10 minutes of in-world time. You may:
        - Change ship statuses (inbound, holding, docked, transiting, departing)
        - Evolve moods based on what has happened
        - Resolve or escalate active events
        - Introduce one new minor development
        - active_events must be a clean list of max 6 items.
        - Each item is one short sentence.
        - REMOVE events that have resolved. REPLACE escalated events, do not append to them.
        - Once a ship has departed, destroyed, or recovered, set its status to "departed"
        - You will be given a new ship with the status of "inbound" for each ship that departs, is destroyed, or recovered. Do not generate new ships on your own. 
        - Update the current_arc with what is happening RIGHT NOW
        - Increment current_time by approximately 10 minutes each update.

        Return only valid JSON matching the exact structure you were given.
        No explanation, no markdown, no commentary. JSON only. 
        Do not include recent_transmissions in your response.
        
        """
    user_prompt = f"""
        Update only what has changed in the world state after 5 transmissions.
        Return only a partial JSON with these fields: ships (changed ships only), active_events, current_arc, meta and gate_status.
        Do not return recent_transmissions.
        Current world state:
        {story_input}

        Transmissions since last update:  {promptRecentTransmissions}

        Advance the simulation. Return partial JSON only, no explanation.
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
            print(f"World State Update Response: {reply}")  # Debugging line

            #recent = world["recent_transmissions"]
            #world = json.loads(reply)
            #world["recent_transmissions"] = recent
            #worldstate_save(world, config.WORLD_STATE_PATH)

            updates = json.loads(reply)

            if "ships" in updates:
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

            to_remove = [
                callsign for callsign, data in world["ships"].items()
                if data.get("status") in ("departed", "destroyed", "recovered")
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

            world["meta"]["tick"] += 1

            if world["meta"]["tick"] % 10 == 0:  # Every 6 ticks, generate world state
                print("\n--- Generating World State ---")
                generate_world_state()
                print("--- World State Updated ---")

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

            time.sleep(0.5) 

    

    except KeyboardInterrupt:
        print("\n--- Comms Terminated ---")
        pygame.mixer.quit()

if __name__ == "__main__":
    main()