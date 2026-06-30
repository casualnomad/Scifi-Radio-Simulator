import random
from pydub import AudioSegment
from pydub.generators import WhiteNoise
from pydub.generators import SignalGenerator
from scipy.signal import butter, lfilter
import numpy as np

def modulate_audio(character):
    # Load your TTS output audio (WAV)
    audio = AudioSegment.from_wav("SFX/temp_TTSoutput.wav")
    samples = np.array(audio.get_array_of_samples())    # Convert to numpy array for filtering
    
    if character == "AI":
        char_ai(audio)
        
    else:
        char_captain(samples, audio)

def char_ai(audio):

    audio.export("SFX/output.wav", format="wav")


def char_captain(samples, audio):

    # Apply bandpass filter for radio voice (300Hz to 3400Hz)
    filtered_samples = bandpass_filter(samples, int(random.uniform(150, 400)), int(random.uniform(1700, 3000)), audio.frame_rate)
    filtered_samples = filtered_samples.astype(np.int16)

    # Create new AudioSegment from filtered samples
    filtered_audio = AudioSegment(
        filtered_samples.tobytes(), 
        frame_rate=audio.frame_rate,
        sample_width=audio.sample_width, 
        channels=audio.channels
    )

    #Add a random amount of static before and after the message
    extra_static = create_dynamic_static(len(filtered_audio) + random.randint(2000, 3000), audio.frame_rate,filtered_audio, target_diff_db=40)

    #Place the audio inside the above static
    combined = extra_static.overlay(filtered_audio, position=random.randint(1000,2500))

    #Export final message
    combined.export("SFX/output.wav", format="wav")

def create_dynamic_static(duration_ms, frame_rate, voice_audio, target_diff_db=40):
    
    voice_db = voice_audio.dBFS #Measures the loudness of the voice

    base_level = voice_db - target_diff_db #base static level: voice minus target difference

    noise = WhiteNoise().to_audio_segment(duration=duration_ms)

    # Calculate the gain needed to bring the noise to the base level
    gain_to_apply = base_level - noise.dBFS
    noise = noise.apply_gain(gain_to_apply) # Apply the correct gain

    #Chops noise into chunks and randomizes each chunks voume
    chunk_size = int(random.uniform(150, 400)) #milliseconds
    chunks = []
    for i in range(0, duration_ms, chunk_size):
          chunk = noise[i:i+chunk_size]

          if random.random() < 0.2:
                chunk = eq_muffle(chunk)

          # Random gain
          gain_change = random.uniform(-3, 3) #subtle shifts only
          chunk = chunk.apply_gain(gain_change)       
          chunks.append(chunk)
    
    static_audio = sum(chunks) #concat all chunks
    return static_audio

def eq_muffle(segment):
    #simulates a muffled or heavy static radio sound

    samples = np.array(segment.get_array_of_samples())
    filtered = bandpass_filter(samples, 1000, 2500, segment.frame_rate) #narrows the bands further than normal
    filtered = filtered.astype(np.int16) 
    return AudioSegment(
          filtered.tobytes(),
          frame_rate = segment.frame_rate,
          sample_width = segment.sample_width,
          channels = segment.channels
    )

# Bandpass filter helper functions
def bandpass_filter(data, lowcut, highcut, fs, order=4):
        b, a = butter_bandpass(lowcut, highcut, fs, order=order)
        y = lfilter(b, a, data)
        return y

def butter_bandpass(lowcut, highcut, fs, order=4):
        nyq = 0.5 * fs
        low = lowcut / nyq
        high = highcut / nyq
        b, a = butter(order, [low, high], btype='band')
        return b, a


