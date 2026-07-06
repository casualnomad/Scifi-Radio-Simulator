import numpy as np
import pygame
import scipy.signal as sig
import threading

# Function to generate white noise
def generate_noise(fs, t):
    noise = np.random.rand(len(t))  # Generate white noise
    # Filter the noise to simulate the ambiance of a space station
    # We'll use a Butterworth low-pass filter with a cutoff frequency of 200 Hz
    nyq = fs / 2  # Nyquist frequency
    cutoff = 200 / nyq  # Cutoff frequency
    b, a = sig.butter(4, cutoff)  # Butterworth filter coefficients
    # Apply the filter to the noise
    filtered_noise = sig.lfilter(b, a, noise)
    return filtered_noise

# Function to play the noise
def play_noise(fs, t):
    while True:
        noise = generate_noise(fs, t)
        # Ensure that highest value is in 16-bit range
        audio = noise * (2**15 - 1) / np.max(np.abs(noise))
        audio = audio.astype(np.int16)
        # Play the noise
        mixer.init()  # Initialize the mixer here (if necessary)
        stream = mixer.sndarray.make_sound(audio)
        stream.play()

# Start playing the noise
fs = 44100  # Sample rate
t = np.arange(0, 10, 1/fs)  # Time array
thread = threading.Thread(target=play_noise, args=(fs, t))
thread.daemon = True  # Set as daemon thread so that it stops when the main thread stops
thread.start()
