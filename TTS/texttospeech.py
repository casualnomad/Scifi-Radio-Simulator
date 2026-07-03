import soundfile as sf
from kittentts import KittenTTS as tts
from TTS.voicemodulation import modulate_audio
import random

m = tts("KittenML/kitten-tts-mini-0.8")

voices = ['Jasper', 'Luna', 'Rosie', 'Hugo', 'Bella', 'Leo']

# -------- TTS Voices -------- #

ai_voice = "Bella"

# -------- TTS Voices -------- #

def generate_tts(character, trimmedtext):
    
    speed = random.uniform(1.0, 1.3)  # Random speed between 1.0 and 1.3
    
    if character == "AI": 
            voice = ai_voice
            speed = 1.2  # AI voice has a fixed speed of 1.2
    if character == "Tower": 
            voice = 'Bruno'
    if character == "Captain": 
            voice = random.choice(voices)
    if character == "Default": 
            voice = random.choice(voices)
        
    audio = m.generate(trimmedtext, voice=voice, speed=speed)
    print(f"Generated TTS for {character} with voice {voice} at speed {speed:.2f}")
    sf.write('SFX/temp_TTSoutput.wav', audio, 24000)
    modulate_audio(character)


    