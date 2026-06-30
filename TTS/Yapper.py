from TTS.voicemodulation import modulate_audio
import wave
import random
from piper import PiperVoice

# -------- TTS Voices -------- #

ai_voice = "en_GB-cori-high"
#capt_voice = ["een_US-joe-medium.onnx", "en_US-arctic-medium", "en_US-ryan-high" "en_US-norman-medium"]
towr_voice = ["en_US-libritts-high"]

# -------- TTS Voices -------- #

def generate_tts(character, trimmedtext):
    
    if character == "AI": 
            voice = ai_voice
    if character == "Tower": 
            voice = random.choice(towr_voice)
    if character == "Captain": 
            voice = random.choice(towr_voice)
    if character == "Default": 
            voice = ai_voice

    voice = PiperVoice.load("./pipervoices/en_US-libritts-high.onnx")
   
    speaker_id = random.choice(list(voice.config.speaker_id_map.keys()))
    print(f"Using speaker ID: {speaker_id}")
    voice.speaker_id = speaker_id

    #voice = PiperVoice.load("./pipervoices/" + voice + ".onnx")

    # Piper 1.3.0 → synthesize() yields AudioChunk → use .audio_int16_bytes
    audio_bytes = b"".join(
        chunk.audio_int16_bytes for chunk in voice.synthesize(trimmedtext)
    )

    sample_rate = voice.config.sample_rate  # from model config

    with wave.open("SFX/temp_TTSoutput.wav", "wb") as wav_file:
        wav_file.setnchannels(1)      # mono
        wav_file.setsampwidth(2)      # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_bytes)
        
    modulate_audio(character)