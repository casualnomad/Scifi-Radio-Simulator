import random
import numpy as np
from pydub import AudioSegment
from pydub.generators import WhiteNoise
from scipy.signal import butter, lfilter

def modulate_audio(character):
    # Load your TTS output audio (WAV)
    audio = AudioSegment.from_wav("SFX/temp_TTSoutput.wav")
    samples = np.array(audio.get_array_of_samples()) # Convert to numpy array
    print("Voice mod Char = " + character)
    
    if character == "AI":
        char_ai(audio)
    elif character == "Captain":
        char_captain(samples, audio)
    else:
       clean_audio(audio)
        

# ==========================================
# 🤖 AI CHARACTER EFFECTS
# ==========================================
def char_ai(audio):
    # Convert pydub audio segment to float32 numpy array for precise DSP math
    samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
    fs = audio.frame_rate
    
    # 1. RING MODULATION (Creates the synthetic, metallic cybernetic timbre)
    mod_freq = 30.0  # 30Hz-45Hz is smooth/robotic, 60Hz+ is harsh/alien
    t = np.arange(len(samples)) / fs
    carrier = np.sin(2 * np.pi * mod_freq * t)
    
    # Blend 40% modulated carrier with 60% clean voice to maintain clarity
    ring_modulated = (samples * carrier * 0.4) + (samples * 0.6)

    # 2. CHORUS / RESONANCE (Simulates a hollow metal chassis/speaker)
    delay_ms = 10  # Micro-delay creates a comb-filter robotic resonance
    delay_samples = int((delay_ms / 1000.0) * fs)
    
    delayed_signal = np.zeros_like(ring_modulated)
    delayed_signal[delay_samples:] = ring_modulated[:-delay_samples]
    
    # Mix original signal with the delayed reflection
    robot_samples = (ring_modulated * 0.7) + (delayed_signal * 0.4)
    
    # 3. HIGH-END BIAS EQ (Removes muddy lows to sound pristine/digitized)
    robot_samples = bandpass_filter(robot_samples, 200, 6500, fs, order=3)

    # Clip safely to 16-bit boundaries and convert back to integers
    robot_samples = np.clip(robot_samples, -32768, 32767).astype(np.int16)

    # Build the final pydub AudioSegment
    ai_audio = AudioSegment(
        robot_samples.tobytes(), 
        frame_rate=fs,
        sample_width=audio.sample_width, 
        channels=audio.channels
    )
    
    # Normalize volume and export
    ai_audio = ai_audio.normalize()
    ai_audio.export("SFX/output.wav", format="wav")
    print("🤖 AI audio processing complete.")


# ==========================================
# 📻 CAPTAIN CHARACTER EFFECTS
# ==========================================
def load_or_create_mic_click(frame_rate, duration_ms=100, pop_freq=120):
    """Generates a soft, hardware PTT mic click and faint static burst."""
    t = np.arange(int((duration_ms / 1000.0) * frame_rate)) / frame_rate
    # Create a quick fading sine wave pop
    pop = np.sin(2 * np.pi * pop_freq * t) * np.exp(-t * 60) 
    
    # FIXED: Drastically lowered amplitude of the noise trailing the pop to prevent loud bursts
    noise = np.random.normal(0, 0.05, len(t)) 
    combined_signal = (pop * 0.5) + (noise * 0.1)
    
    # FIXED: Lowered max multiplier from 32767 to 8000 to cap physical digital clipping volume
    combined_signal = np.clip(combined_signal * 8000, -32768, 32767).astype(np.int16)
    
    return AudioSegment(
        combined_signal.tobytes(),
        frame_rate=frame_rate,
        sample_width=2,
        channels=1
    )

def char_captain(samples, audio):
    # 1. Apply bandpass filter for radio restriction (300Hz to 3400Hz standard)
    filtered_samples = bandpass_filter(samples, int(random.uniform(150, 400)), int(random.uniform(1700, 3000)), audio.frame_rate)
    
    # 2. INTERMODULATION DISTORTION (Simulates cheap overdriven military speakers)
    filtered_samples = filtered_samples.astype(np.float32)
    gain_factor = 2.2  # Amplify the signal aggressively to blow out the peaks
    filtered_samples *= gain_factor
    filtered_samples = np.clip(filtered_samples, -32768, 32767).astype(np.int16)

    # Create new AudioSegment from processed samples
    filtered_audio = AudioSegment(
        filtered_samples.tobytes(), 
        frame_rate=audio.frame_rate,
        sample_width=audio.sample_width, 
        channels=audio.channels
    )

    # 3. MIC PTT SQUELCH CLICKS
    mic_on = load_or_create_mic_click(audio.frame_rate, duration_ms=80)
    mic_off = load_or_create_mic_click(audio.frame_rate, duration_ms=120)
    
    # Stitch clicks directly onto the voice transmission track
    voice_with_clicks = mic_on + filtered_audio + mic_off

    # 4. RANDOM SIGNAL RECEPTION QUALITY
    # FIXED: Increased target offsets so background static stays pushed beneath the voice track
    reception = random.choice(["clear", "noisy", "heavy_interference"])
    if reception == "clear":
        target_diff = random.randint(40, 50) 
    elif reception == "noisy":
        target_diff = random.randint(30, 38)
    else:
        target_diff = random.randint(22, 28) 

    # Add background environmental static padding
    static_duration = len(voice_with_clicks) + random.randint(2000, 3500)
    extra_static = create_dynamic_static(static_duration, audio.frame_rate, voice_with_clicks, target_diff_db=target_diff)

    # Drop our transmission cleanly inside the static pad
    combined = extra_static.overlay(voice_with_clicks, position=random.randint(1000, 2000))

    # Export final message
    combined.export("SFX/output.wav", format="wav")
    print(f"📻 Captain audio processing complete (Signal state: {reception}).")


def create_dynamic_static(duration_ms, frame_rate, voice_audio, target_diff_db=40):
    voice_db = voice_audio.dBFS  # Measures the loudness of the voice
    base_level = voice_db - target_diff_db  # base static level relative to speech

    noise = WhiteNoise().to_audio_segment(duration=duration_ms)
    gain_to_apply = base_level - noise.dBFS
    noise = noise.apply_gain(gain_to_apply)

    # Chops noise into chunks and randomizes each chunk's volume
    chunk_size = int(random.uniform(150, 400)) # milliseconds
    chunks = []
    for i in range(0, duration_ms, chunk_size):
        chunk = noise[i:i+chunk_size]

        if random.random() < 0.2:
            chunk = eq_muffle(chunk)

        # FIXED: Narrowed random variance window so static doesn't spike unpredictably
        gain_change = random.uniform(-1, 1) 
        chunk = chunk.apply_gain(gain_change)       
        chunks.append(chunk)
    
    # FIXED: Added a global safety master dampener (-12) to the mixed static array 
    # to guarantee it sits safely in the background beneath the voice
    static_audio = sum(chunks).apply_gain(-12) 
    return static_audio

def eq_muffle(segment):
    samples = np.array(segment.get_array_of_samples())
    filtered = bandpass_filter(samples, 1000, 2500, segment.frame_rate)
    filtered = filtered.astype(np.int16) 
    return AudioSegment(
        filtered.tobytes(),
        frame_rate = segment.frame_rate,
        sample_width = segment.sample_width,
        channels = segment.channels
    )

# ==========================================
# 🤫 ASMR MUFFLED CHARACTER EFFECTS
# ==========================================
def char_asmr_muffled(audio):
    samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
    fs = audio.frame_rate

    # Cut off everything above 800Hz to give it a thick "through the wall" pillow sound
    muffled_samples = lowpass_filter(samples, cut_off=800, fs=fs, order=4)

    # Boost the warm proximity frequencies to enhance vocal chord resonance
    gain_factor = 3.0  
    muffled_samples *= gain_factor

    # Strip sub-bass rumble beneath 60Hz to keep the warmth clean
    muffled_samples = bandpass_filter(muffled_samples, 60, 1200, fs, order=2)
    muffled_samples = np.clip(muffled_samples, -32768, 32767).astype(np.int16)

    muffled_audio = AudioSegment(
        muffled_samples.tobytes(), 
        frame_rate=fs,
        sample_width=audio.sample_width, 
        channels=audio.channels
    )
    
    # Normalize pulls quiet breathing textures up close to the ear
    muffled_audio = muffled_audio.normalize()
    muffled_audio.export("SFX/output.wav", format="wav")
    print("🤫 Muffled ASMR audio processing complete.")
    
    
def clean_audio(audio):
    
    audio.export("SFX/output.wav", format="wav")
    print("Clean audio processing complete.")


# ==========================================
# 🎛️ DSP FILTER HELPERS
# ==========================================
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

def lowpass_filter(data, cut_off, fs, order=4):
    b, a = butter_lowpass(cut_off, fs, order=order)
    y = lfilter(b, a, data)
    return y

def butter_lowpass(cut_off, fs, order=4):
    nyq = 0.5 * fs
    low = cut_off / nyq
    b, a = butter(order, low, btype='low')
    return b, a