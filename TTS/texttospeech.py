import soundfile as sf
from kittentts import KittenTTS as tts
from TTS.voicemodulation import modulate_audio
import random

m = tts("KittenML/kitten-tts-nano-0.1")


# -------- TTS Voices -------- #

ai_voice = "expr-voice-4-f"
capt_voice1 = "expr-voice-2-f" 
capt_voice2 = "expr-voice-3-m" 
towr_voice1 = "expr-voice-5-m" 
towr_voice2 = "expr-voice-5-f"

# -------- TTS Voices -------- #

def generate_tts(character, trimmedtext):
    
    if character == "AI": 
            voice = ai_voice
    if character == "Tower": 
            voice = random.choice([towr_voice1,towr_voice2])
    if character == "Captain": 
            voice = random.choice([capt_voice1,capt_voice2])
    if character == "Default": 
            voice = ai_voice
        
    audio = m.generate(text= trimmedtext, voice=voice)
    sf.write('SFX/temp_TTSoutput.wav', audio, 24000)
    modulate_audio(character)