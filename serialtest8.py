from collections import deque
import serial
import time
import numpy as np
from scipy.signal import find_peaks, peak_widths

# --- Configuration ---
PORT = 'COM4'
BAUDRATE = 115200
BUFFER_DURATION = 1.5  # seconds of signal to analyze
PEAK_MIN_HEIGHT = 500
PEAK_MIN_DISTANCE = 10
PEAK_WIDTH_THRESHOLD = 0.015
AMPLITUDE_THRESHOLD = 2500 #300
ENERGY_THRESHOLD = 2e7 #2e7
PEAK_COUNT_THRESHOLD = 5 #3
LOCKOUT_TIME = 2.5  # seconds between peak detections

# --- Setup Serial and Buffers ---
ser = serial.Serial(port=PORT, baudrate=BAUDRATE, bytesize=8, parity='N', stopbits=1)
print("Connected to:", ser.name)

adc_buffer = deque()
time_buffer = deque()
start_time = time.time()
detecting_peak = True
last_peak_time = -10

# --- Classification Function ---
def classify_signal(adc, time):
    adc_np = np.array(adc)
    time_np = np.array(time)

    # Peak detection
    peaks, properties = find_peaks(adc_np, height=PEAK_MIN_HEIGHT, distance=PEAK_MIN_DISTANCE)
    if len(peaks) == 0:
        return "NO PEAK", None, None,None

    widths_result = peak_widths(adc_np, peaks, rel_height=0.5)
    widths = widths_result[0] * np.mean(np.diff(time_np))

    num_peaks = len(peaks)
    max_amplitude = np.max(adc_np)
    main_peak_width = widths[np.argmax(properties['peak_heights'])] if num_peaks > 0 else 0
    signal_energy = np.sum(np.square(adc_np))

    # Rule-based object classification (original rules)
    score = 0
    score += max_amplitude > AMPLITUDE_THRESHOLD
    score += num_peaks >= PEAK_COUNT_THRESHOLD
    score += main_peak_width < PEAK_WIDTH_THRESHOLD
    score += signal_energy > ENERGY_THRESHOLD

    object_type = "COIN" if score >= 1 else "ERASER"

    return object_type, max_amplitude, signal_energy,num_peaks

# --- Height Classification Function ---
def classify_height(object_type, peak, energy,num_peaks):
    if object_type == "COIN":


        if peak >=3800 and energy > 4.5e7:
            print(energy)
            print(peak)
            print(num_peaks)
            return "10cm distance, 30cm height"

        elif peak >900 and energy > 1e6  :
            print(energy)
            print(peak)
            print(num_peaks)
            return "30cm distance 30cm height"


        
        elif peak >1100 and peak < 4100 :
            print(energy)
            print(peak)
            print(num_peaks)
            return "10cm distance 10cm height"

        elif peak < 1100 :
            print(energy)
            print(peak)
            print(num_peaks)
            return "30cm distance 10cm height"


        
    elif object_type == "ERASER":
        if peak > 1900 and energy > 1e7:
            print(energy)
            print(peak)
            print(num_peaks)
            return "10cm distance, 30cm height" #height
        
        elif (peak>=1900 and peak <3800): #1600 -1700-2000,1846 #12 #15 ,14,11,14,12
            print(energy)
            print(peak)
            print(num_peaks)
            return "30cm distance, 30cm height" #height
        
        elif (peak>=1100 and peak <1900): #2237,1464,
            print(energy)
            print(peak)
            print(num_peaks)
            return "10cm distance, 10cm height" #height

        elif peak < 1100: #671,598,612,524,
            print(energy)
            print(peak)
            print(num_peaks)
            return "30cm distance,10cm height" #height
        

        

        

    else:
        return "Unknown"

# --- Main Loop ---
try:
    while True:
        line = ser.readline().decode('ascii').strip()
        current_time = time.time() - start_time

        if "ADC Value" in line:
            try:
                value = int(line.split('=')[1].strip())
            except (IndexError, ValueError):
                continue  # Skip invalid lines

            adc_buffer.append(value)
            time_buffer.append(current_time)

            # Remove old data outside the buffer window
            while len(time_buffer) > 0 and current_time - time_buffer[0] > BUFFER_DURATION:
                adc_buffer.popleft()
                time_buffer.popleft()

            # Analyze when allowed
            if detecting_peak and len(adc_buffer) > 30:
                object_type, peak_value, energy_value, num_peaks = classify_signal(adc_buffer, time_buffer)
                if object_type != "NO PEAK":
                    height = classify_height(object_type, peak_value, energy_value,num_peaks)
                    print(f"{object_type} dropped from {height} detected at {current_time:.2f}s")
                    detecting_peak = False
                    last_peak_time = current_time

            # Reset detection after lockout
            if not detecting_peak and (current_time - last_peak_time) >= LOCKOUT_TIME:
                detecting_peak = True

except KeyboardInterrupt:
    print("Stopped by user.")
    ser.close()


